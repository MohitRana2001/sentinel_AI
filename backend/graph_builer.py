"""
Graph building utilities with graceful fallbacks for local development.

The original implementation relied on LangChain experimental modules that are
currently incompatible with the LangChain 1.x packages. This module provides a
drop-in replacement that exposes `graph`, `llm`, and `LLMGraphTransformer`
symbols so the processor service can continue to run even without the original
dependencies.
"""
from __future__ import annotations

import os
import re
import unicodedata
from typing import List, Optional

from langchain_core.documents import Document

try:
    from langchain_neo4j import Neo4jGraph
except Exception:  # pragma: no cover - optional dependency
    Neo4jGraph = None  # type: ignore

from langchain_community.graphs.graph_document import (
    GraphDocument,
    Node,
    Relationship,
)

try:
    from langchain_experimental.graph_transformers import (
        LLMGraphTransformer as ExperimentalGraphTransformer,
    )
except Exception:  # pragma: no cover - optional dependency
    ExperimentalGraphTransformer = None  # type: ignore

try:
    from langchain_ollama.chat_models import ChatOllama
except Exception:  # pragma: no cover - optional dependency
    ChatOllama = None  # type: ignore

# Import config for flexible configuration
try:
    from config import settings

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    GRAPH_LLM_MODEL = settings.GRAPH_LLM_MODEL
    GRAPH_LLM_URL = settings.GRAPH_LLM_URL
except ImportError:  # pragma: no cover - fallback when config missing
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "password"
    NEO4J_DATABASE = "neo4j"
    GRAPH_LLM_MODEL = "gemma3:4b"
    GRAPH_LLM_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Neo4j graph initialisation (optional in local dev)
# ---------------------------------------------------------------------------
graph = None  # type: ignore[assignment]

if Neo4jGraph is not None:
    try:
        graph = Neo4jGraph(
            refresh_schema=False,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
            url=NEO4J_URI,
        )
    except TypeError:
        # Older versions expect positional URL argument
        try:
            graph = Neo4jGraph(
                NEO4J_URI,
                username=NEO4J_USERNAME,
                password=NEO4J_PASSWORD,
                database=NEO4J_DATABASE,
                refresh_schema=False,
            )
        except Exception as exc:  # pragma: no cover - external service may be absent
            print(f"Warning: could not connect to Neo4j at {NEO4J_URI}: {exc}")
            graph = None
    except Exception as exc:  # pragma: no cover
        print(f"Warning: could not connect to Neo4j at {NEO4J_URI}: {exc}")
        graph = None
else:
    print("Warning: langchain_neo4j not available; graph persistence disabled.")


# ---------------------------------------------------------------------------
# LLM initialisation (optional)
# ---------------------------------------------------------------------------
if ChatOllama is not None:
    try:
        llm = ChatOllama(model=GRAPH_LLM_MODEL, base_url=GRAPH_LLM_URL)
    except Exception as exc:  # pragma: no cover - Ollama may not be running
        print(f"Warning: could not initialise Ollama graph LLM: {exc}")
        llm = None
else:
    llm = None


# ---------------------------------------------------------------------------
# Fallback graph transformer
# ---------------------------------------------------------------------------
class SimpleGraphTransformer:
    """
    Minimal graph transformer used when LangChain experimental modules are
    unavailable. It extracts capitalised tokens as entities and links adjacent
    entities with a generic relationship so downstream components receive a
    non-empty graph.
    """

    def __init__(self, llm: Optional[object] = None):
        self.llm = llm

    def convert_to_graph_documents(
        self, documents: List[Document]
    ) -> List[GraphDocument]:
        graph_documents: List[GraphDocument] = []

        for document in documents:
            text = document.page_content or ""
            tokens = re.findall(r"\b[A-Z][A-Za-z]{2,}\b", text)
            unique_tokens = list(dict.fromkeys(tokens))[:25]

            if unique_tokens:
                nodes = [
                    Node(
                        id=token,
                        type="Entity",
                        properties={
                            "label": token,
                            "canonical_label": self._canonical(token),
                            "document_id": document.metadata.get("document_id") if document.metadata else None,
                        },
                    )
                    for token in unique_tokens
                ]
                relationships = [
                    Relationship(
                        source=nodes[idx],
                        target=nodes[idx + 1],
                        type="RELATED_TO",
                        properties={},
                    )
                    for idx in range(len(nodes) - 1)
                ]
            else:
                nodes = [
                    Node(
                        id=f"document-{hash(document.page_content)}",
                        type="Document",
                        properties={"label": "Document"},
                    )
                ]
                relationships = []

            graph_documents.append(
                GraphDocument(
                    nodes=nodes,
                    relationships=relationships,
                    source=document,
                )
            )

        return graph_documents

    @staticmethod
    def _canonical(value: str) -> str:
        """Normalise entity labels for simple entity resolution."""
        value = unicodedata.normalize("NFKD", value)
        value = re.sub(r"[^a-z0-9]+", "-", value.lower())
        return value.strip("-")


# ---------------------------------------------------------------------------
# Hybrid graph transformer that prefers the experimental implementation
# ---------------------------------------------------------------------------
class _HybridGraphTransformer:
    """
    Wrapper that prefers LangChain's LLMGraphTransformer when available,
    otherwise falls back to the lightweight heuristic transformer above.
    """

    def __init__(self, llm: Optional[object] = None):
        self.llm = llm
        self._fallback = SimpleGraphTransformer(llm=llm)
        self._delegate = None

        if llm is not None and ExperimentalGraphTransformer is not None:
            try:
                self._delegate = ExperimentalGraphTransformer(llm=llm)
            except Exception as exc:  # pragma: no cover - external service may fail
                print(
                    "Warning: LangChain experimental LLMGraphTransformer unavailable; "
                    f"falling back to heuristic graph builder: {exc}"
                )
                self._delegate = None
        elif ExperimentalGraphTransformer is None:
            print(
                "Warning: langchain_experimental not available; "
                "using heuristic graph builder."
            )
        elif llm is None:
            print(
                "Warning: Graph LLM not initialised; "
                "using heuristic graph builder."
            )

    def convert_to_graph_documents(
        self, documents: List[Document]
    ) -> List[GraphDocument]:
        if self._delegate is not None:
            try:
                return self._delegate.convert_to_graph_documents(documents)
            except Exception as exc:  # pragma: no cover
                print(
                    "Warning: LLM-based graph extraction failed; "
                    f"falling back to heuristic graph builder: {exc}"
                )
        return self._fallback.convert_to_graph_documents(documents)


# Expose symbol for compatibility with the rest of the codebase
LLMGraphTransformer = _HybridGraphTransformer


__all__ = [
    "graph",
    "llm",
    "LLMGraphTransformer",
    "GraphDocument",
    "Node",
    "Relationship",
]
