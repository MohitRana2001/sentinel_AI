from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from config import settings
import models


class VectorStore:
    
    def __init__(self, db: Session):
        self.db = db
        self.embeddings = None
        self.embedding_available = True
        
        try:
            self.embeddings = OllamaEmbeddings(
                model=settings.EMBEDDING_MODEL,
                base_url=settings.EMBEDDING_LLM_URL
            )
        except Exception as exc:
            self.embedding_available = False
            print(f"Embedding model unavailable ({exc}). Falling back to keyword search.")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def add_document_chunks(
        self,
        document_id: int,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[int]:

        chunks = self.text_splitter.split_text(text)
        
        print(f"Created {len(chunks)} chunks for document {document_id}")
        
        chunk_ids = []
        for idx, chunk_text in enumerate(chunks):
            embedding_vector = None
            if self.embedding_available and self.embeddings is not None:
                try:
                    embedding_vector = self.embeddings.embed_query(chunk_text)
                except Exception as exc:
                    self.embedding_available = False
                    embedding_vector = None
                    print(f"Failed to generate embedding ({exc}). Using fallback mode.")
            
            chunk = models.DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding_vector,
                chunk_metadata=metadata or {}
            )
            self.db.add(chunk)
            self.db.flush()  # Get the ID
            chunk_ids.append(chunk.id)
        
        self.db.commit()
        print(f"Stored {len(chunks)} chunks with embeddings")
        
        return chunk_ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        document_id: int = None,
        job_id: str = None,
        user: Optional[models.User] = None
    ) -> List[Dict[str, Any]]:
        
        query_embedding = None
        if self.embedding_available and self.embeddings is not None:
            try:
                query_embedding = self.embeddings.embed_query(query)
            except Exception as exc:
                self.embedding_available = False
                print(f"Failed to embed query ({exc}). Using fallback keyword search.")
                query_embedding = None
        
        # Build query
        query_obj = self.db.query(models.DocumentChunk).join(models.Document)

        if user:
            if user.rbac_level == models.RBACLevel.STATE:
                query_obj = query_obj.filter(models.Document.state_id == user.state_id)
            elif user.rbac_level == models.RBACLevel.DISTRICT:
                query_obj = query_obj.filter(
                    models.Document.state_id == user.state_id,
                    models.Document.district_id == user.district_id,
                )
            else:
                query_obj = query_obj.filter(
                    models.Document.state_id == user.state_id,
                    models.Document.district_id == user.district_id,
                    models.Document.station_id == user.station_id,
                )
    
        if document_id:
            query_obj = query_obj.filter(models.DocumentChunk.document_id == document_id)
    
        if job_id:
            query_obj = query_obj.filter(models.Document.job_id == job_id)
        
        if query_embedding is not None:
            from sqlalchemy import text
            
            results = query_obj.filter(models.DocumentChunk.embedding.isnot(None)).order_by(
                text(f"embedding <=> '{query_embedding}'::vector")
            ).limit(k).all()
        else:
            # Fallback: keyword search by simple substring match
            like_query = f"%{query}%"
            results = query_obj.filter(
                models.DocumentChunk.chunk_text.ilike(like_query)
            ).limit(k).all()
            
            if len(results) < k:
                # If not enough matches, pad with recent chunks
                extra = query_obj.order_by(models.DocumentChunk.created_at.desc()).limit(k - len(results)).all()
                # Avoid duplicates
                seen_ids = {r.id for r in results}
                results.extend([r for r in extra if r.id not in seen_ids])
        
        return [
            {
                "chunk_text": chunk.chunk_text,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.chunk_metadata
            }
            for chunk in results
        ]


def vectorise_and_store_alloydb(
    db: Session,
    document_id: int,
    text_content: str,
    summary: str = None
) -> List[int]:
    vector_store = VectorStore(db)
    
    # Store document chunks
    chunk_ids = vector_store.add_document_chunks(
        document_id=document_id,
        text=text_content,
        metadata={"source": "document"}
    )
    
    # Store summary if provided
    if summary:
        summary_ids = vector_store.add_document_chunks(
            document_id=document_id,
            text=summary,
            metadata={"source": "summary"}
        )
        chunk_ids.extend(summary_ids)
    
    return chunk_ids
