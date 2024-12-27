# config.py
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def get_env_variable(var_name: str, required: bool = True, default: str = None) -> str:
    """
    Get environment variable with proper error handling
    
    Parameters:
    -----------
    var_name : str
        Name of the environment variable
    required : bool
        Whether the variable is required
    default : str
        Default value if not required and not found
    """
    value = os.getenv(var_name)
    
    if value is None and required:
        logger.error(f"Required environment variable {var_name} not found")
        raise ValueError(f"Required environment variable {var_name} not found")
    
    if value is None and not required:
        logger.warning(f"Optional environment variable {var_name} not found, using default: {default}")
        return default
        
    return value

# Database configuration (required)
MYSQL_USER = get_env_variable("MYSQL_USER")
MYSQL_PASSWORD = get_env_variable("MYSQL_PASSWORD")
MYSQL_HOST = get_env_variable("MYSQL_HOST")
MYSQL_DATABASE = get_env_variable("MYSQL_DATABASE")

# OpenAI configuration (optional)
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY", required=False, default=None)

# Other optional configurations
IGNORED_TABLES = get_env_variable("IGNORED_TABLES", required=False, default="").split(",")