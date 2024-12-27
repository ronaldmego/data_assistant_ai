# config.py
from dotenv import load_dotenv
import os

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Obtener las variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# config/config.py
MAX_SCHEMA_CHUNKS = 3
TEMPORAL_TABLE_WINDOW = 3  # número de tablas temporales recientes a considerar