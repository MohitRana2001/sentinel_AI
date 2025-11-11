from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

import google.generativeai as genai

from config import settings


class GoogleDocAgent:

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for GoogleDocAgent")
        self.api_key = api_key
        self.model_name = model or settings.GOOGLE_CHAT_MODEL or "gemini-2.5-flash"
        genai.configure(api_key=self.api_key)
        
        # Configure generation settings for better responses
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config=generation_config
        )

    # def _load_reference_paths(self) -> List[str]:
    #     """
    #     Load reference files if specified in settings.
    #     NOTE: Reference files should be small (<10KB). Large files will cause token limit issues!
    #     """
    #     base_paths = settings.google_agent_reference_paths
    #     contents: List[str] = []
    #     max_size = 10_000
        
    #     for raw_path in base_paths:
    #         try:
    #             path = Path(raw_path).expanduser()
    #             if not path.exists():
    #                 continue
                    
    #             # Check file size before reading
    #             file_size = path.stat().st_size
    #             if file_size > max_size:
    #                 print(f"⚠️  Skipping large reference file {raw_path} ({file_size} bytes > {max_size} bytes)")
    #                 continue
                
    #             text = path.read_text(encoding="utf-8")
    #             contents.append(text)
    #         except Exception as exc:  # pragma: no cover - filesystem optional
    #             print(f"⚠️  Could not read reference file {raw_path}: {exc}")
    #     return contents

    def build_prompt(
        self,
        question: str,
        chunks: Iterable[Mapping[str, str]],
        metadata: Optional[Mapping[str, str]] = None,
        include_static_refs: bool = False,  # Changed to False by default
    ) -> str:
        """
        Create a prompt string that embeds retrieved document chunks and optional metadata.
        
        Args:
            question: The user's question
            chunks: Retrieved document chunks (should be limited to 5-10 chunks)
            metadata: Optional metadata about the job/document
            include_static_refs: Whether to include static reference files (default: False)
        """
        references = []
        
        # Add document chunks (should already be limited by caller)
        for idx, chunk in enumerate(chunks, start=1):
            text = chunk.get("chunk_text", "")
            if not text.strip():
                continue
                
            # Allow longer chunks for better context (up to 2000 chars)
            if len(text) > 2000:
                text = text[:2000] + "...[truncated]"
            
            doc_id = chunk.get("document_id", "unknown")
            chunk_idx = chunk.get("chunk_index", "unknown")
            references.append(
                f"[Excerpt {idx}] (Document ID: {doc_id}, Chunk: {chunk_idx})\n{text.strip()}"
            )

        # Only add static references if explicitly requested AND if they're small
        # if include_static_refs:
        #     static_refs = self._load_reference_paths()
        #     for idx, ref_text in enumerate(static_refs, start=len(references) + 1):
        #         if len(ref_text) > 1000:
        #             ref_text = ref_text[:1000] + "...[truncated]"
        #         references.append(f"[Reference {idx}]\n{ref_text.strip()}")

        prompt_parts = [
            "You are Sentinel AI's intelligent document analysis assistant.",
            "Your role is to provide accurate, helpful answers based on the document excerpts provided below.",
            "",
            "Guidelines:",
            "- Answer questions directly and concisely based on the provided excerpts",
            "- Always cite the specific excerpt number when referencing information (e.g., 'According to Excerpt 2...')",
            "- If the answer is not found in the excerpts, clearly state that you don't have that information",
            "- Provide context and explanation to make your answers helpful and easy to understand",
            "- If multiple excerpts contain relevant information, synthesize them into a coherent response",
        ]
        
        if references:
            prompt_parts.append("\n--- Document Excerpts ---")
            prompt_parts.append("\n\n".join(references))
            prompt_parts.append("\n--- End of Excerpts ---")
        else:
            prompt_parts.append("\n(No document excerpts available)")
        
        # Add metadata context if available
        if metadata:
            context_info = []
            if metadata.get("job_id"):
                context_info.append(f"Job ID: {metadata['job_id']}")
            if metadata.get("document_id"):
                context_info.append(f"Document ID: {metadata['document_id']}")
            if context_info:
                prompt_parts.append(f"\nContext: {', '.join(context_info)}")
        
        prompt_parts.append(f"\nUser Question: {question}")
        prompt_parts.append("\nYour Response:")
        
        return "\n".join(prompt_parts)

    def generate(
        self,
        question: str,
        chunks: Iterable[Mapping[str, str]],
        metadata: Optional[Mapping[str, str]] = None,
        include_static_refs: bool = False,
    ) -> str:
        """
        Generate a response to the question based on document chunks.
        
        Args:
            question: The user's question
            chunks: Retrieved document chunks (max 5-10 recommended)
            metadata: Optional metadata
            include_static_refs: Whether to include static reference files (default: False)
        """
        prompt = self.build_prompt(question, chunks, metadata, include_static_refs)
        
        # Debug: show prompt length
        print(f"Prompt length: {len(prompt)} characters ({len(prompt.split())} words)")
        
        try:
            response = self.model.generate_content(prompt)
            if response.candidates and len(response.candidates) > 0:
                return response.text.strip()
            return "I could not generate a response. The model may have filtered the content."
        except Exception as exc:
            print(f"Gemini generation error: {exc}")
            return f"Error generating response: {str(exc)}"
