import os
import requests
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from src.utils import load_config
from src.cache_manager import QueryCache, generate_schema_hash
import logging

logger = logging.getLogger(__name__)

# Initialize global cache
_query_cache = QueryCache()

class DirectGeminiLLM(BaseChatModel):
    """Direct Gemini API implementation"""
    model_name: str = "gemini-2.5-flash"
    api_key: str = ""
    temperature: float = 0.7
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate response using direct Gemini API"""
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if isinstance(msg, (HumanMessage, SystemMessage)) else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "topP": 0.9
            }
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.messages import AIMessage
        
        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    def _llm_type(self):
        return "direct_gemini"
    
    @property
    def _identifying_params(self):
        return {"model_name": self.model_name}

def get_llm():
    config = load_config()
    provider = config.get("llm_provider", "ollama")
    model_name = config.get("model_name", "llama3")
    
    if provider == "ollama":
        return ChatOllama(model=model_name)
    elif provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment variables")
            raise ValueError("GOOGLE_API_KEY is required for Google provider")
        logger.info("Using Google Gemini API")
        return DirectGeminiLLM(model_name=model_name, api_key=api_key)
    elif provider == "openai":
        return ChatOpenAI(model=model_name, api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "anthropic":
        return ChatAnthropic(model=model_name, api_key=os.getenv("ANTHROPIC_API_KEY"))
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
