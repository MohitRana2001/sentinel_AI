import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from storage_config import storage_manager
from config import settings
from database import SessionLocal
import models

from graph_builer import graph, llm, llm_transformer, LLMGraphTransformer
from langchain_core.documents import Document
import traceback
from collections import defaultdict
import unicodedata
import re
from datetime import datetime, timezone
import time


def _canonical(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-")


class GraphProcessorService:
    
    def __init__(self):
        if llm_transformer is not None:
            self.llm_transformer = llm_transformer
            print("Using LLMGraphTransformer (initialized in graph_builer.py)")
        else:
            print("LLM Transformer unavailable - graph building will fail")
            self.llm_transformer = None
        
        if graph is None:
            print("Neo4j not connected - graph persistence disabled")
            print("Check NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD in .env")
    
    def process_job(self, message: dict):
        """
        Build knowledge graph for a document
        
        Message format:
        {
            "job_id": "uuid",
            "document_id": 123,
            "gcs_text_path": "path/to/text.txt",
            "username": "user@example.com"
        }
        """
        job_start_time = time.time()
        
        job_id = message.get("job_id")
        document_id = message.get("document_id")
        gcs_text_path = message.get("gcs_text_path")
        username = message.get("username", "unknown")
        
        print(f"Graph Processor received job for document: {document_id}")
        print(f"Username: {username}")
        print(f"Starting graph processing at {time.strftime('%H:%M:%S')}")
        
        db = SessionLocal()
        text = None
        try:
            text = storage_manager.download_text(gcs_text_path)
        except Exception as e:
            print(f"Error downloading extracted text file: {gcs_text_path}")
            print(f"Exception: {repr(e)}")
            print(f"This likely means the document processor failed to process this file or GCS is unreachable.")
            print(f"Skipping graph processing for document {document_id}")
            return
        if not text or not text.strip():
            print(f"Extracted text for document {document_id} is empty or missing after download.")
            print(f"This likely means document processor produced no output or there was a storage issue.")
            print(f"Skipping graph processing for document {document_id}")
            return
        
        try:
            max_chars = 5000
            if len(text) > max_chars:
                text = text[:max_chars]
                print(f"Text truncated to {max_chars} chars for graph extraction")
            
            print(f"Extracting entities and relationships...")
            
            start_time = time.time()
            
            documents = [Document(
                page_content=text, 
                metadata={
                    "document_id": str(document_id),
                    "job_id": job_id
                }
            )]
            
            print(f"Calling LLM for entity extraction...")
            graph_documents = self.llm_transformer.convert_to_graph_documents(documents)
            print(f"{graph_documents}")
            extraction_time = time.time() - start_time
            print(f"Entity extraction took {extraction_time:.2f} seconds")
            
            if not graph_documents:
                print(f"No graph documents generated")
                return
            
            nodes_count = len(graph_documents[0].nodes)
            relationships_count = len(graph_documents[0].relationships)
            
            print(f"Extracted {nodes_count} nodes and {relationships_count} relationships")
            
            # Get document info
            document = db.query(models.Document).filter(
                models.Document.id == document_id
            ).first()
            
            if not document:
                print(f"Document {document_id} not found")
                return
            
            # Store in Neo4j
            if graph is not None:
                try:
                    self._sync_neo4j(job_id, document, graph_documents[0], username)
                except Exception as exc:
                    print(f"Could not persist graph to Neo4j: {exc}")
                    traceback.print_exc()
            else:
                print("Neo4j graph unavailable; skipping graph persistence.")
            
            # Store graph metadata in AlloyDB
            if document:
                existing_entities = db.query(models.GraphEntity).join(models.Document).filter(
                    models.Document.job_id == job_id
                ).all()
                canonical_index = defaultdict(list)
                for existing in existing_entities:
                    existing_props = existing.properties or {}
                    canonical = existing_props.get("canonical_label") or _canonical(existing.entity_name)
                    canonical_index[canonical].append(existing)
                
                per_doc_counts = defaultdict(int)
                node_id_map = {}
                
                # Store entities in database for quick access
                for node in graph_documents[0].nodes:
                    node_props = dict(node.properties) if hasattr(node, 'properties') else {}
                    label = node_props.get("label", node.id)
                    canonical = node_props.get("canonical_label") or _canonical(label)
                    node_props["canonical_label"] = canonical
                    node_props["document_id"] = document_id
                    
                    per_doc_counts[canonical] += 1
                    entity_identifier = f"{job_id}-{document_id}-{canonical}-{per_doc_counts[canonical]}"
                    
                    entity = models.GraphEntity(
                        document_id=document_id,
                        entity_id=entity_identifier,
                        entity_name=label,
                        entity_type=node.type if hasattr(node, 'type') else 'Entity',
                        properties=node_props
                    )
                    db.add(entity)
                    node_id_map[node.id] = entity_identifier
                    
                    # Cross-document links (entity resolution)
                    for existing in canonical_index.get(canonical, []):
                        if existing.document_id != document_id:
                            if not self._relationship_exists(db, entity_identifier, existing.entity_id):
                                cross_rel = models.GraphRelationship(
                                    source_entity_id=entity_identifier,
                                    target_entity_id=existing.entity_id,
                                    relationship_type="CROSS_DOC_MATCH",
                                    properties={
                                        "canonical_label": canonical,
                                        "source_document_id": document_id,
                                        "target_document_id": existing.document_id,
                                    }
                                )
                                db.add(cross_rel)
                    canonical_index[canonical].append(entity)
                
                # Store relationships
                for rel in graph_documents[0].relationships:
                    source_id = node_id_map.get(rel.source.id)
                    target_id = node_id_map.get(rel.target.id)
                    if not source_id or not target_id:
                        continue
                    rel_props = dict(rel.properties) if hasattr(rel, 'properties') else {}
                    rel_props.setdefault("document_id", document_id)
                    rel_props.setdefault("job_id", job_id)
                    relationship = models.GraphRelationship(
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relationship_type=rel.type,
                        properties=rel_props
                    )
                    db.add(relationship)
                
                db.commit()
            
            total_time = time.time() - job_start_time
            print(f"Graph building completed for document {document_id}")
            print(f"Total graph processing time: {total_time:.2f} seconds")
            
            # Check if this was the last document to be processed for this job
            job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()
            if job:
                # Count how many documents have been fully processed (have graph entities)
                documents_with_graphs = db.query(models.Document).join(
                    models.GraphEntity,
                    models.Document.id == models.GraphEntity.document_id
                ).filter(
                    models.Document.job_id == job_id
                ).distinct().count()
                
                print(f"Job {job_id}: {documents_with_graphs}/{job.total_files} documents have graphs")
                
                # If all files have been graph-processed, mark job as completed
                if documents_with_graphs >= job.total_files:
                    job.status = models.JobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    print(f"Job {job_id} marked as COMPLETED")
                    print(f"Job completion latency from graph start: {total_time:.2f} seconds")
            
        except Exception as e:
            print(f"Error in graph processor: {e}")
            traceback.print_exc()
        finally:
            db.close()
    
    @staticmethod
    def _relationship_exists(db, source_id: str, target_id: str) -> bool:
        return db.query(models.GraphRelationship).filter(
            models.GraphRelationship.source_entity_id == source_id,
            models.GraphRelationship.target_entity_id == target_id,
            models.GraphRelationship.relationship_type == "CROSS_DOC_MATCH"
        ).first() is not None

    def _sync_neo4j(self, job_id: str, document: models.Document, graph_document, username: str) -> None:
        """
        Sync graph to Neo4j using LangChain's native method + User and Document nodes
        """
        if graph is None:
            return
        
        print(f"Syncing graph for document {document.id}: {len(graph_document.nodes)} nodes, {len(graph_document.relationships)} relationships")
        
        # Step 1: Use LangChain's native graph.add_graph_documents() 
        try:
            # Add metadata to nodes for tracking
            for node in graph_document.nodes:
                if not hasattr(node, 'properties') or node.properties is None:
                    node.properties = {}
                node.properties['job_id'] = job_id
                node.properties['document_id'] = str(document.id)
                node.properties['canonical_label'] = _canonical(node.id)
            
            # Add metadata to relationships
            for rel in graph_document.relationships:
                if not hasattr(rel, 'properties') or rel.properties is None:
                    rel.properties = {}
                rel.properties['job_id'] = job_id
                rel.properties['document_id'] = str(document.id)
            
            # Use LangChain's method with include_source=True to create Document nodes
            graph.add_graph_documents(
                [graph_document],
                baseEntityLabel=True,
                include_source=True
            )
            print(f"Added graph documents to Neo4j using LangChain's native method")
            
        except Exception as e:
            print(f"Error using add_graph_documents: {e}")
            traceback.print_exc()
        
        # Step 2: Create/Merge User node
        print(f"Linking document to user: {username}")
        user_query = """
        MERGE (u:User {username: $username})
        ON CREATE SET u.created_at = datetime()
        SET u.updated_at = datetime()
        """
        try:
            graph.query(user_query, {"username": username})
        except Exception as e:
            print(f"Error creating User node: {e}")
        
        # Step 3: Link User to Document with OWNS relationship
        link_query = """
        MERGE (u:User {username: $username})
        MERGE (d:Document {document_id: $doc_id})
        MERGE (u)-[r:OWNS]->(d)
            ON CREATE SET 
            r.created_at = datetime(),
            r.job_id = $job_id
        SET r.updated_at = datetime()
        """
        try:
            graph.query(
                link_query, 
            {
                    "username": username, 
                    "doc_id": str(document.id),
                    "job_id": job_id
                }
            )
            print(f"Document successfully linked to user {username}")
        except Exception as e:
            print(f"Error linking document to user: {e}")
        
        # Step 4: Link Document node to its entities (CONTAINS_ENTITY relationships)
        for node in graph_document.nodes:
            canonical = _canonical(node.id)
            entity_link_query = """
                MATCH (d:Document {document_id:$document_id})
                MATCH (e) WHERE e.id = $entity_id OR e.canonical_label = $canonical
                MERGE (d)-[r:CONTAINS_ENTITY]->(e)
                ON CREATE SET r.created_at = datetime()
            SET 
                r.canonical_label = $canonical,
                r.updated_at = datetime()
            """
            try:
                graph.query(
                    entity_link_query,
                {
                    "document_id": str(document.id),
                    "entity_id": node.id,
                    "canonical": canonical,
                },
            )
            except Exception as e:
                print(f"Error linking entity {node.id} to document: {e}")
        
        # Step 5: Entity resolution - create SHARES_ENTITY between documents
        entities_in_doc = graph.query(
            """
            MATCH (d:Document {document_id:$document_id})-[:CONTAINS_ENTITY]->(e)
            RETURN DISTINCT e.id as entity_id, 
                   COALESCE(e.canonical_label, toLower(replace(e.id, ' ', '-'))) as canonical
            """,
            {"document_id": str(document.id)},
        )
        
        for entity_record in entities_in_doc:
            canonical = entity_record["canonical"]
            # Find other documents with this entity
            share_entity_query = """
                MATCH (d1:Document {document_id:$document_id})
                MATCH (e) WHERE COALESCE(e.canonical_label, toLower(replace(e.id, ' ', '-'))) = $canonical
                MATCH (d2:Document)-[:CONTAINS_ENTITY]->(e)
                WHERE d2.document_id <> $document_id AND d1.job_id = d2.job_id
                MERGE (d1)-[r:SHARES_ENTITY {entity_canonical:$canonical}]->(d2)
                ON CREATE SET r.created_at = datetime()
                SET r.updated_at = datetime()
            """
            try:
                graph.query(
                    share_entity_query,
                {
                    "document_id": str(document.id),
                    "canonical": canonical,
                },
            )
            except Exception as e:
                # This is expected for first document, silently continue
                pass
        
        print(f"Neo4j sync complete for document {document.id}")


def main():
    """Main entry point"""
    print("Starting Graph Processor Service...")
    print(f"Using Redis Queue for true parallel processing")
    print(f"Listening to queue: {settings.REDIS_QUEUE_GRAPH}")
    
    service = GraphProcessorService()
    
    # Listen to Redis queue (each worker gets different messages)
    redis_pubsub.listen_queue(
        queue_name=settings.REDIS_QUEUE_GRAPH,
        callback=service.process_job
    )


if __name__ == "__main__":
    main()
