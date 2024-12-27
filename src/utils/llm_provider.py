# src/utils/llm_provider.py
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM  # Actualizado
from langchain_core.language_models.chat_models import BaseChatModel
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class LLMProvider:
    """Provider class for Language Model selection and configuration"""
    
    @staticmethod
    def get_llm(provider: str = "openai", model_name: Optional[str] = None, **kwargs) -> BaseChatModel:
        """
        Get the specified language model instance
        
        Parameters:
        -----------
        provider : str
            The LLM provider to use ('openai' or 'ollama')
        model_name : Optional[str]
            The specific model name to use (e.g., 'gpt-4' for OpenAI or 'llama2' for Ollama)
        **kwargs : dict
            Additional configuration parameters for the model
        """
        try:
            if provider == "openai":
                    api_key = st.session_state.get('OPENAI_API_KEY')
                    if not api_key:
                        raise ValueError("OpenAI API key not found in session state")
                        
                    return ChatOpenAI(
                        model=model_name or "gpt-4",
                        temperature=kwargs.get('temperature', 0.7),
                        openai_api_key=api_key
                    )
                
            elif provider == "ollama":
                return OllamaLLM(  # Actualizado
                    model=model_name or "llama3:8b-instruct-q8_0",
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
            logger.warning("Requests library not found. Please install it with 'pip install requests'")
            return False

    @staticmethod
    def list_available_models(provider: str) -> list:
        """List available models for the specified provider"""
        if provider == "openai":
            return ["gpt-4", "gpt-3.5-turbo"]
        elif provider == "ollama":
            return ["llama3:8b-instruct-q8_0", "llama2", "mistral", "codellama"]
        return []