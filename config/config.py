# config/config.py
from dotenv import load_dotenv
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Cargar las variables de entorno
load_dotenv()

def get_env_variable(var_name: str, required: bool = True, default: str = None) -> str:
    value = os.getenv(var_name)
    
    if value is None and required:
        logger.error(f"Required environment variable {var_name} not found")
        raise ValueError(f"Required environment variable {var_name} not found")
    
    if value is None and not required:
        logger.warning(f"Optional environment variable {var_name} not found, using default: {default}")
        return default
        
    return value

# OpenAI configuration
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY", required=False, default=None)

# Parse OpenAI Models from environment
def parse_openai_models() -> Dict:
    models_str = get_env_variable("OPENAI_MODELS", required=False, default=(
        "gpt-4o-mini|GPT-4 Mini (Most Economic)|gpt-4o-mini|1;"
        "gpt-4o-mini-2024-07-18|GPT-4 Mini July|gpt-4o-mini-2024-07-18|2;"
        "gpt-4o-2024-08-06|GPT-4 Turbo August|gpt-4o-2024-08-06|3;"
        "gpt-4o|GPT-4 Turbo (High Performance)|gpt-4o|4"
    ))
    
    models_dict = {}
    for model_str in models_str.split(';'):
        if not model_str:
            continue
        try:
            key, name, model_id, priority = model_str.split('|')
            models_dict[key] = {
                'name': name,
                'model': model_id,
                'priority': int(priority)
            }
        except ValueError as e:
            logger.error(f"Error parsing model configuration: {model_str}")
            continue
    
    if not models_dict:
        logger.warning("No valid models found in configuration, using defaults")
        return {
            'gpt-4o-mini': {
                'name': 'GPT-4 Mini (Most Economic)',
                'model': 'gpt-4o-mini',
                'priority': 1
            }
        }
    
    return models_dict

# Get OpenAI Models configuration
OPENAI_MODELS = parse_openai_models()
DEFAULT_MODEL = min(OPENAI_MODELS.items(), key=lambda x: x[1]['priority'])[0]

# Database configuration
MYSQL_USER = get_env_variable("MYSQL_USER")
MYSQL_PASSWORD = get_env_variable("MYSQL_PASSWORD")
MYSQL_HOST = get_env_variable("MYSQL_HOST")
MYSQL_DATABASE = get_env_variable("MYSQL_DATABASE")