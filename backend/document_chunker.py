from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
from langchain_chroma import Chroma
import pickle
import sys

# Import config for flexible configuration
try:
    from config import settings
    OLLAMA_HOST = settings.EMBEDDING_LLM_URL
    EMBEDDING_MODEL = settings.EMBEDDING_MODEL
    CHUNK_SIZE = settings.CHUNK_SIZE
    CHUNK_OVERLAP = settings.CHUNK_OVERLAP
except ImportError:
    # Fallback for standalone usage
    OLLAMA_HOST = 'http://localhost:11434'
    EMBEDDING_MODEL = "embeddinggemma:latest"
    CHUNK_SIZE = 2000
    CHUNK_OVERLAP = 100

def vectorise_and_store(obj, vector_store, t, filename="stub"):
    """
    Original function - kept for backward compatibility
    Works with ChromaDB or any LangChain vector store
    """
    if t=="file":
        with open(obj) as f:
            text = f.read()
        chunk_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = chunk_splitter.split_text(text)
        chroma_documents = []
        for chunk in chunks:
            document = Document(page_content=chunk,metadata={"source":"chunk","filename":obj})
            chroma_documents.append(document)
        uuids = [str(uuid4()) for _ in range(len(chroma_documents))]
        vector_store.add_documents(documents=chroma_documents, ids=uuids)
    else:
        summary_document = Document(page_content=obj,metadata={"source":"summary","filename":filename})
        uuid = str(uuid4())
        vector_store.add_documents(documents=[summary_document], ids=[uuid])

if __name__=="__main__":
    if len(sys.argv)!=2:
        print("Only one positional argument expected. Please specify directory")
        sys.exit()
    pdf_path = sys.argv[-1]
    embed = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
    vector_store = Chroma(
        collection_name="main_collection",
        embedding_function=embed,
        host="localhost",
    )
    with open(f'{pdf_path}/final_file_paths.pkl','rb') as file:
        final_file_paths = pickle.load(file)
    for final_file in final_file_paths:
        summary_file_name = final_file.split(".")[-2].split('/')[-1]
        summary_file_name += "-summary.txt"
        summary=""
        with open(f"{pdf_path}/{summary_file_name}",'r') as f:
            summary = f.read()
        vectorise_and_store(final_file,vector_store,"file")
        vectorise_and_store(summary,vector_store,"content",final_file)
