"""
Ollama agent for document-aware chat.

Uses a local Ollama model (e.g., Gemma) to answer questions based on
document chunks retrieved from the vector store.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

from ollama import Client

from config import settings


class OllamaDocAgent:
    """Wrapper around a local Ollama model for document grounded chat."""

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        self.model_name = model or settings.CHAT_LLM_MODEL
        self.host = host or settings.CHAT_LLM_URL
        try:
            self.client = Client(host=self.host)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ollama at {self.host}. Is it running?") from e

    def build_prompt(
        self,
        question: str,
        chunks: Iterable[Mapping[str, str]],
        metadata: Optional[Mapping[str, str]] = None,
    ) -> str:
        """
        Create a prompt string that embeds retrieved document chunks.
        This logic is shared with the GoogleDocAgent.
        """
        references = []
        
        for idx, chunk in enumerate(chunks, start=1):
            text = chunk.get("chunk_text", "")
            if not text.strip():
                continue
                
            if len(text) > 2500:
                text = text[:2500] + "...[truncated]"
            
            doc_id = chunk.get("document_id", "unknown")
            chunk_idx = chunk.get("chunk_index", "unknown")
            references.append(
                f"[Excerpt {idx}] (Document ID: {doc_id}, Chunk: {chunk_idx})\n{text.strip()}"
            )

        prompt_parts = [
            "You are an intelligent document analysis assistant.",
            "Your role is to provide accurate, helpful answers based on the document excerpts provided below.",
            "",
            "Guidelines:",
            "- Answer questions directly and concisely based on the provided excerpts.",
            "- Always cite the specific excerpt number when referencing information (e.g., 'According to Excerpt 2...').",
            "- If the answer is not found in the excerpts, clearly state that you don't have that information.",
            "- If multiple excerpts contain relevant information, synthesize them into a coherent response.",
        ]
        
        if references:
            prompt_parts.append("\n--- Document Excerpts ---")
            prompt_parts.append("\n\n".join(references))
            prompt_parts.append("\n--- End of Excerpts ---")
        else:
            prompt_parts.append("\n(No document excerpts available)")
        
        prompt_parts.append(f"\nUser Question: {question}")
        prompt_parts.append("\nYour Response:")
        
        return "\n".join(prompt_parts)

    def generate(
        self,
        question: str,
        chunks: Iterable[Mapping[str, str]],
        metadata: Optional[Mapping[str, str]] = None,
    ) -> str:
        """
        Generate a response to the question based on document chunks using Ollama.
        """
        prompt = self.build_prompt(question, chunks, metadata)
        
        print(f"📝 Ollama Prompt length: {len(prompt)} characters ({len(prompt.split())} words)")

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ],
            )
            if response and response.get("message"):
                return response["message"]["content"].strip()
            return "I could not generate a response from the local model."
        except Exception as exc:
            print(f"❌ Ollama generation error: {exc}")
            return f"Error generating response from local model: {str(exc)}"