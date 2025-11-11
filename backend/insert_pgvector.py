import psycopg2 
from langchain_ollama import OllamaEmbeddings
import json


def insert_pgvector(doc_chunks, document_id: int):

    conn = psycopg2.connect(
        host="10.0.2.35",
        database="sentinel_db",
        user="postgres",
        password="newpassword",
        port=5432
    )
    
    embedding = OllamaEmbeddings(
        model="embeddinggemma:latest",
        base_url='http://10.0.2.222:11434'
    )
    
    cur = conn.cursor()
    chunks_inserted = 0
    
    if len(doc_chunks) > 0:
        print('========Got multiple Chunks==========')
        for chunks in doc_chunks:
            for chunk in chunks:
                chunk_text = chunk.get('enriched_chunk')
                print(f'Processing chunk {chunk_text[:100]}...')
                
                # document_id = chunk.get('file_path')
                file_path = chunk.get('file_path', '')
                metadata_data = {
                    'file_path': file_path,
                    'source': 'hybrid_chunker'
                }
                # metadata_data = {'file_path': document_id}
                embedding_data = embedding.embed_query(chunk_text)
                chunk_index = chunk.get('chunk_index')
                
                sql_query = """
                    INSERT INTO document_chunks 
                    (document_id, chunk_index, chunk_text, embedding, metadata) 
                    VALUES (%s, %s, %s, %s, %s);
                """
                
                cur.execute(
                    sql_query,
                    (document_id, chunk_index, chunk_text, embedding_data, json.dumps(metadata_data))
                )
                chunks_inserted += 1;
        
        conn.commit()
        print(f'Successfully inserted {chunks_inserted} documents with their chunks')
    
    cur.close()
    conn.close()