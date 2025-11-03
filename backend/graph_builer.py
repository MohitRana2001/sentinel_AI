from __future__ import annotations

import os
from langchain_core.documents import Document

try:
    from langchain_neo4j import Neo4jGraph
    NEO4J_AVAILABLE = True
except Exception:
    Neo4jGraph = None
    NEO4J_AVAILABLE = False
    print("⚠️  langchain_neo4j not available")

try:
    from langchain_experimental.graph_transformers import LLMGraphTransformer
    GRAPH_TRANSFORMER_AVAILABLE = True
except Exception:
    LLMGraphTransformer = None
    GRAPH_TRANSFORMER_AVAILABLE = False
    print("⚠️  LLMGraphTransformer not available")

try:
    from langchain_ollama.chat_models import ChatOllama
    OLLAMA_AVAILABLE = True
except Exception:
    ChatOllama = None
    OLLAMA_AVAILABLE = False
    print("⚠️  ChatOllama not available")

try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except Exception:
    genai = None
    ChatGoogleGenerativeAI = None
    GEMINI_AVAILABLE = False

# Import config
try:
    from config import settings
    NEO4J_URI = settings.NEO4J_URI
    NEO4J_USERNAME = settings.NEO4J_USERNAME
    NEO4J_PASSWORD = settings.NEO4J_PASSWORD
    NEO4J_DATABASE = settings.NEO4J_DATABASE
    GRAPH_LLM_MODEL = settings.GRAPH_LLM_MODEL
    GRAPH_LLM_URL = settings.GRAPH_LLM_URL
    USE_GEMINI_FOR_DEV = settings.USE_GEMINI_FOR_DEV
    GEMINI_API_KEY = settings.GEMINI_API_KEY
except ImportError:
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "password"
    NEO4J_DATABASE = "neo4j"
    GRAPH_LLM_MODEL = "gemma3:4b"
    GRAPH_LLM_URL = "http://localhost:11434"
    USE_GEMINI_FOR_DEV = False
    GEMINI_API_KEY = ""

# ---------------------------------------------------------------------------
# Neo4j Graph Initialization
# ---------------------------------------------------------------------------
graph = None

if NEO4J_AVAILABLE:
    try:
        graph = Neo4jGraph(
            refresh_schema=False,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
            url=NEO4J_URI,
        )
        print(f"✅ Connected to Neo4j at {NEO4J_URI}")
    except Exception as exc:
        print(f"❌ Could not connect to Neo4j at {NEO4J_URI}: {exc}")
        graph = None
else:
    print("❌ Neo4j not available")

# ---------------------------------------------------------------------------
# LLM Initialization (Dev: Gemini, Prod: Ollama)
# ---------------------------------------------------------------------------
llm = None
llm_transformer = None

# Try Gemini for dev mode
if USE_GEMINI_FOR_DEV and GEMINI_API_KEY and GEMINI_AVAILABLE:
    try:
        print("🔷 Initializing Gemini for graph building (DEV MODE)")
        genai.configure(api_key=GEMINI_API_KEY)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=GEMINI_API_KEY,
            temperature=0
        )
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print("✅ Gemini graph transformer initialized")
    except Exception as exc:
        print(f"⚠️  Could not initialize Gemini, falling back to Ollama: {exc}")
        llm = None
        llm_transformer = None

# Fallback to Ollama for production or if Gemini fails
if llm is None and OLLAMA_AVAILABLE:
    try:
        print(f"🔧 Initializing Ollama ({GRAPH_LLM_MODEL}) for graph building (PROD MODE)")
        llm = ChatOllama(model=GRAPH_LLM_MODEL, base_url=GRAPH_LLM_URL)
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print(f"Ollama graph transformer initialized with {GRAPH_LLM_MODEL}")
    except Exception as exc:
        print(f"Could not initialize Ollama graph LLM: {exc}")
        llm = None
        llm_transformer = None


__all__ = [
    "graph",
    "llm",
    "llm_transformer",
    "LLMGraphTransformer",
]
