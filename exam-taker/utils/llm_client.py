import os
import json
import requests
from typing import Optional

class LLMClient:
    def __init__(self, provider: str = "ollama", model_name: str = "llama3", api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.provider == "ollama":
            self.base_url = base_url or "http://localhost:11434"
        elif self.provider == "openai":
            self.base_url = base_url or "https://api.openai.com/v1"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def generate_response(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """
        Generates a response from the configured LLM.
        """
        if self.provider == "ollama":
            return self._query_ollama(prompt, system_prompt)
        elif self.provider == "openai":
            return self._query_openai(prompt, system_prompt)
        return ""

    def _query_ollama(self, prompt: str, system_prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        
        # Combine system and user prompt for simple Ollama models if they don't support system roles explicitly in /generate
        # But /api/chat is better for system prompts. Let's use /api/chat if possible, or just /api/generate with a combined prompt.
        # Using /api/chat is safer for structured instructions.
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            return f"Error querying Ollama: {str(e)}"

    def _query_openai(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            return "Error: OpenAI API key not found."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error querying OpenAI: {str(e)}"

    def get_embedding(self, text: str) -> list:
        """
        Generates an embedding vector for the given text.
        """
        if self.provider == "ollama":
            url = f"{self.base_url}/api/embeddings"
            # Switch to embedding model if not set, or use current if user knows what they are doing.
            # Best practice: use simple separated config, but for now reuse model_name
            # The user requested 'all-minilm:l6-v2' specifically.
            model = self.model_name if "minilm" in self.model_name else "all-minilm:l6-v2"
            
            payload = {
                "model": model,
                "prompt": text
            }
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                return response.json().get("embedding", [])
            except Exception as e:
                print(f"Error getting embedding: {e}")
                return []
        else:
             # Fallback or strict error
             return []
