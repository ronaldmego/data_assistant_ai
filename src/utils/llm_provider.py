# src/utils/llm_provider.py
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM
from langchain_core.language_models.chat_models import BaseChatModel
import streamlit as st
import logging
from config.config import OPENAI_MODELS, DEFAULT_MODEL

logger = logging.getLogger(__name__)

class LLMProvider:
    """Provider class for Language Model selection and configuration"""
    
    @staticmethod
    def get_llm(provider: str = "openai", model_name: Optional[str] = None, **kwargs) -> BaseChatModel:
        """
        Get the specified language model instance
        """
        try:
            if provider == "openai":
                api_key = st.session_state.get('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OpenAI API key not found in session state")
                
                # Use the model mapping to get the actual model name
                model_info = OPENAI_MODELS.get(model_name or DEFAULT_MODEL)
                if not model_info:
                    model_info = OPENAI_MODELS[DEFAULT_MODEL]
                
                return ChatOpenAI(
                    model=model_info['model'],
                    temperature=kwargs.get('temperature', 0.7),
                    openai_api_key=api_key
                )
            
            elif provider == "ollama":
                return OllamaLLM(
                    model=model_name or "llama2",
                    temperature=kwargs.get('temperature', 0.7),
                    base_url=kwargs.get('base_url', "http://localhost:11434")
                )
            
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            logger.error(f"Error initializing LLM provider: {str(e)}")
            raise

    @staticmethod
    def check_ollama_availability() -> bool:
        """Check if Ollama is running and available"""
        try:
            import requests
            try:
                response = requests.get("http://localhost:11434/api/version", timeout=2)
                return response.status_code == 200
            except requests.RequestException:
                return False
        except ImportError:
            logger.warning("Requests library not found")
            return False

    @staticmethod
    def list_available_models(provider: str) -> list:
        """List available models for the specified provider"""
        if provider == "openai":
            return sorted(
                OPENAI_MODELS.keys(),
                key=lambda x: OPENAI_MODELS[x]['priority']
            )
        elif provider == "ollama":
            return ["llama3:8b-instruct-q8_0", "mistral", "codellama"]
        return []

    @staticmethod
    def get_model_display_name(model_name: str) -> str:
        """Get the display name for a model"""
        if model_info := OPENAI_MODELS.get(model_name):
            return model_info['name']
        return model_name