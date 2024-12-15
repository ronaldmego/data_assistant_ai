# database.py
from config.config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE
from langchain_community.utilities import SQLDatabase
import os
from typing import List, Dict, Optional
from sqlalchemy import text, create_engine, inspect
import logging
import mysql.connector

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection() -> Dict:
    """Test database connection and return status"""
    try:
        # Primero probar conexión básica
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        if conn.is_connected():
            # Si la conexión es exitosa, obtener las tablas
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "tables": tables,
                "error": None
            }
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {
            "success": False,
            "tables": [],
            "error": str(e)
        }

# Construir el URI de conexión para MySQL
mysql_uri = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DATABASE}'

try:
    # Inicializar conexiones
    db = SQLDatabase.from_uri(mysql_uri)
    engine = create_engine(mysql_uri)
except Exception as e:
    logger.error(f"Error initializing database connections: {str(e)}")
    db = None
    engine = None

def get_ignored_tables() -> List[str]:
    """Get list of tables to ignore from environment variable"""
    ignored_tables = os.getenv('IGNORED_TABLES', '')
    return [table.strip() for table in ignored_tables.split(',') if table.strip()]

def get_all_tables() -> List[str]:
    """Get all tables from the database using SQLAlchemy inspector"""
    try:
        if not engine:
            raise Exception("Database engine not initialized")
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Found tables: {tables}")
        return tables
    except Exception as e:
        logger.error(f"Error getting tables: {str(e)}")
        return []

def get_schema(input_data: Optional[dict] = None) -> str:
    """Get schema information for all tables except ignored ones"""
    try:
        if not db:
            raise Exception("Database connection not initialized")
            
        all_tables = get_all_tables()
        ignored_tables = get_ignored_tables()
        
        logger.info(f"All tables: {all_tables}")
        logger.info(f"Ignored tables: {ignored_tables}")
        
        # Filter out ignored tables
        tables_to_use = [table for table in all_tables if table not in ignored_tables]
        logger.info(f"Tables to use: {tables_to_use}")
        
        if not tables_to_use:
            return "No tables available for querying."
        
        # Get schema info for remaining tables
        schema_info = db.get_table_info(table_names=tables_to_use)
        return schema_info
    except Exception as e:
        logger.error(f"Error getting schema information: {str(e)}")
        return f"Error getting schema information: {str(e)}"

def run_query(query: str) -> List[tuple]:
    """Execute SQL query"""
    try:
        if not db:
            raise Exception("Database connection not initialized")
            
        result = db.run(query)
        logger.info(f"Query executed successfully")
        return result
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise