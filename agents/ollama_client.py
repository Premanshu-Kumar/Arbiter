"""
Ollama Client - Interface for local LLM interactions
"""
import requests
import json
from typing import Dict, Any, Optional
import config


class OllamaClient:
    """Client for interacting with Ollama local LLM server"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.timeout = 60
    
    def check_connection(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> list:
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            print(f"Error listing models: {str(e)}")
            return []
    
    def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Ollama"""
        model = model or config.CODER_MODEL
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise Exception("Request to Ollama timed out")
        except Exception as e:
            raise Exception(f"Error generating text: {str(e)}")
    
    def generate_code(
        self,
        prompt: str,
        model: str = None,
        language: str = "python"
    ) -> str:
        """Generate code using coding-specific model"""
        model = model or config.CODER_MODEL
        
        system_prompt = f"""You are an expert {language} programmer. 
Generate clean, efficient, and well-commented code.
Only output the code without any additional explanation."""
        
        return self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for code
        )
    
    def chat(self, messages: list, model: str = None) -> str:
        """Chat interface with message history"""
        model = model or config.REASONING_MODEL
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '')
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Error in chat: {str(e)}")
