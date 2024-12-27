import os
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_env_variable(var_name: str, required: bool = True) -> str:
    """
    Get environment variable with validation
    """
    value = os.getenv(var_name)
    if required and not value:
        logger.error(f"Required environment variable {var_name} not found")
        raise ValueError(f"Required environment variable {var_name} not found")
    return value

# Required configurations
OPENAI_API_KEY = get_env_variable('OPENAI_API_KEY')
MYSQL_USER = get_env_variable('MYSQL_USER')
MYSQL_PASSWORD = get_env_variable('MYSQL_PASSWORD')
MYSQL_HOST = get_env_variable('MYSQL_HOST')
MYSQL_DATABASE = get_env_variable('MYSQL_DATABASE')

# Optional configurations with defaults
IGNORED_TABLES = os.getenv('IGNORED_TABLES', '').split(',')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4')
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))