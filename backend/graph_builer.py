from __future__ import annotations

import os
from langchain_core.documents import Document

try:
    from langchain_neo4j import Neo4jGraph
    NEO4J_AVAILABLE = True
except Exception:
    Neo4jGraph = None
    NEO4J_AVAILABLE = False
    print("langchain_neo4j not available")

try:
    from langchain_experimental.graph_transformers import LLMGraphTransformer
    GRAPH_TRANSFORMER_AVAILABLE = True
except Exception:
    LLMGraphTransformer = None
    GRAPH_TRANSFORMER_AVAILABLE = False
    print("LLMGraphTransformer not available")

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except Exception:
    ChatOpenAI = None
    OPENAI_AVAILABLE = False
    print("ChatOpenAI not available")

# Optional Gemini via LangChain (for local dev)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    GOOGLE_GENAI_AVAILABLE = True
except Exception:
    ChatGoogleGenerativeAI = None
    GOOGLE_GENAI_AVAILABLE = False
    print("ChatGoogleGenerativeAI not available")
# Optional Ollama chat fallback (for local 11434 endpoints)
try:
    from langchain_ollama import ChatOllama  # type: ignore
    OLLAMA_AVAILABLE = True
except Exception:
    ChatOllama = None
    OLLAMA_AVAILABLE = False
    print("ChatOllama (Ollama) not available")

# Import config
try:
    from config import settings
    NEO4J_URI = settings.NEO4J_URI
    NEO4J_USERNAME = settings.NEO4J_USERNAME
    NEO4J_PASSWORD = settings.NEO4J_PASSWORD
    NEO4J_DATABASE = settings.NEO4J_DATABASE
    GRAPH_LLM_MODEL = settings.GRAPH_LLM_MODEL
    GRAPH_LLM_URL = settings.GRAPH_LLM_URL
except ImportError:
    NEO4J_URI = "bolt://34.47.152.177:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "Google@123"
    NEO4J_DATABASE = "neo4j"
    GRAPH_LLM_MODEL = "google/gemma-3-4b-it"
    GRAPH_LLM_URL = "http://10.0.2.4:8000"
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
        print(f"Connected to Neo4j at {NEO4J_URI}")
    except Exception as exc:
        print(f"Could not connect to Neo4j at {NEO4J_URI}: {exc}")
        graph = None
else:
    print("Neo4j not available")

llm = None
llm_transformer = None

initialized = False

# Prefer Ollama when URL hints at Ollama default port or explicit host
prefer_ollama = (
    ("11434" in str(GRAPH_LLM_URL)) or
    ("ollama" in str(GRAPH_LLM_URL).lower())
)

# 1) Local dev: Gemini via google-genai if enabled and available
try_gemini = False
try:
    from config import settings as _settings
    try_gemini = (
        getattr(_settings, 'USE_GEMINI_FOR_DEV', False)
        and bool(getattr(_settings, 'GEMINI_API_KEY', ''))
    )
except Exception:
    try_gemini = False

if try_gemini and GOOGLE_GENAI_AVAILABLE:
    try:
        print("Initializing Gemini (ChatGoogleGenerativeAI) for local development")
        model_name = GRAPH_LLM_MODEL
        if not isinstance(model_name, str) or not model_name.lower().startswith("gemini"):
            try:
                from config import settings as _s
                model_name = getattr(_s, 'GOOGLE_CHAT_MODEL', 'gemini-2.0-flash-exp')
            except Exception:
                model_name = 'gemini-2.0-flash-exp'
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=getattr(_settings, 'GEMINI_API_KEY', None),
            temperature=0,
        )
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print(f"Graph transformer initialized with {model_name} (Gemini)")
            initialized = True
    except Exception as exc:
        print(f"Gemini initialization failed: {exc}")

# 2) Ollama path when URL suggests Ollama
if not initialized and prefer_ollama and OLLAMA_AVAILABLE:
    try:
        print(f"Falling back to ChatOllama at: {GRAPH_LLM_URL}")
        llm = ChatOllama(
            base_url=GRAPH_LLM_URL,
            model=GRAPH_LLM_MODEL,
            temperature=0,
            timeout=90,
        )
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print(f"Graph transformer initialized with {GRAPH_LLM_MODEL} (Ollama)")
            initialized = True
    except Exception as exc:
        print(f"ChatOllama initialization failed: {exc}")

if not initialized and OPENAI_AVAILABLE:
    try:
        print(f"Initializing ChatOpenAI (OpenAI-compatible) at: {GRAPH_LLM_URL}")
        # Add a sensible client timeout and no retries to avoid hanging indefinitely
        llm = ChatOpenAI(
            base_url=f"{GRAPH_LLM_URL}/v1",
            api_key="lm-studio",  # placeholder key for LM Studio / compatible servers
            model=GRAPH_LLM_MODEL,
            temperature=0,
            timeout=90,
            max_retries=0,
        )
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print(f"Graph transformer initialized with {GRAPH_LLM_MODEL} (OpenAI-compatible)")
            initialized = True
    except Exception as exc:
        print(f"ChatOpenAI initialization failed: {exc}")

# Fallback to Ollama if available and not initialized yet
if not initialized and OLLAMA_AVAILABLE:
    try:
        print(f"Falling back to ChatOllama at: {GRAPH_LLM_URL}")
        llm = ChatOllama(
            base_url=GRAPH_LLM_URL,
            model=GRAPH_LLM_MODEL,
            temperature=0,
            timeout=30,
        )
        if GRAPH_TRANSFORMER_AVAILABLE:
            llm_transformer = LLMGraphTransformer(llm=llm)
            print(f"Graph transformer initialized with {GRAPH_LLM_MODEL} (Ollama)")
            initialized = True
    except Exception as exc:
        print(f"ChatOllama initialization failed: {exc}")

if not initialized:
    print("No LLM initialized for graph transformation")


__all__ = [
    "graph",
    "llm",
    "llm_transformer",
    "LLMGraphTransformer",
]
