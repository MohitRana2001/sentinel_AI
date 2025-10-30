"""
Gemini API Client for Local Development
USE ONLY FOR TESTING - Replace with Gemma/Ollama for production
"""
import os
import google.generativeai as genai
from typing import Optional

class GeminiClient:
    """Client for Google Gemini API (local development only)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("✅ Gemini API configured (LOCAL DEV MODE)")
        else:
            self.model = None
            print("⚠️  No Gemini API key found. Set GEMINI_API_KEY environment variable.")
    
    def generate_summary(self, text: str, max_words: int = 200) -> str:
        """Generate summary using Gemini"""
        if not self.model:
            return "Error: Gemini API key not configured"
        
        prompt = f"""Summarize the following text in {max_words} words or less. 
Be concise and capture the key points:

{text}

Summary:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Gemini summary error: {e}")
            return f"Error generating summary: {str(e)}"
    
    def translate_text(self, text: str, target_language: str = "English") -> str:
        """Translate text using Gemini"""
        if not self.model:
            return "Error: Gemini API key not configured"
        
        prompt = f"""Translate the following text to {target_language}:

{text}

Translation:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Gemini translation error: {e}")
            return f"Error translating: {str(e)}"
    
    def transcribe_audio(self, text: str) -> str:
        """
        Placeholder for audio transcription
        In production, use Gemma3:12b multimodal
        For local dev, just return the input or use speech-to-text API
        """
        if not self.model:
            return "Error: Gemini API key not configured"
        
        # For local dev, we can't actually transcribe audio with text API
        # This is a placeholder
        return f"[Audio transcription placeholder - use Gemma3:12b multimodal in production]\n{text}"
    
    def chat(self, query: str, context: str = "") -> str:
        """Chat/RAG using Gemini"""
        if not self.model:
            return "Error: Gemini API key not configured"
        
        prompt = f"""Based on the following context, answer the user's question:

Context:
{context}

Question: {query}

Answer:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Gemini chat error: {e}")
            return f"Error: {str(e)}"


# Singleton instance
gemini_client = GeminiClient()

