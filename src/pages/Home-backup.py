# src/pages/Home.py
import sys
from pathlib import Path
import streamlit as st
import logging
import os

# Añadir el directorio raíz al path de manera robusta
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# AHORA sí podemos importar módulos desde src
from src.utils.logging_config import setup_logging
logger = setup_logging()

# Importar config
from config.config import OPENAI_API_KEY, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE

# Configuración inicial de la página
st.set_page_config(
    page_title="🤖 Quipu AI, your Data Analyst Assistant",
    page_icon="🤖",
    layout="wide"
)

# La configuración básica de logging ya no es necesaria porque setup_logging() la maneja
logger = logging.getLogger(__name__)


def initialize_session_state():
    """Initialize all session state variables"""
    logger.info("Initializing session state...")
    
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'debug_logs' not in st.session_state:
        st.session_state['debug_logs'] = []
    if 'OPENAI_API_KEY' not in st.session_state:
        st.session_state['OPENAI_API_KEY'] = OPENAI_API_KEY
    if 'DB_CONFIG' not in st.session_state:
        st.session_state['DB_CONFIG'] = {
            'user': MYSQL_USER,
            'password': MYSQL_PASSWORD,
            'host': MYSQL_HOST,
            'database': MYSQL_DATABASE
        }

# Initialize session state first
initialize_session_state()

# Initialize session state first
initialize_session_state()

try:
    # Import components - ACTUALIZADO CON RUTAS COMPLETAS
    from src.utils.database import get_all_tables, test_database_connection
    from src.utils.chatbot import generate_sql_chain, generate_response_chain
    from src.services.data_processing import handle_query_and_response
    from src.services.rag_service import initialize_rag_components
    from src.components.debug_panel import display_debug_section
    from src.components.history_view import display_history
    from src.components.query_interface import display_query_interface
    from src.layouts.footer import display_footer
    from src.layouts.header import display_header

    logger.info("All components loaded successfully")
except Exception as e:
    logger.error(f"Failed to import required components: {str(e)}")
    st.error(f"Failed to import required components: {str(e)}")
    st.stop()

def display_table_selection():
    """Display table selection interface"""
    try:
        tables = get_all_tables()
        if not tables:
            st.sidebar.error("No tables found in database.")
            return []
        
        st.sidebar.write("Select tables to query:")
        selected_tables = []
        
        for table in tables:
            if st.sidebar.checkbox(f"{table}", value=True, key=f"table_{table}"):
                selected_tables.append(table)
                
        if selected_tables:
            st.sidebar.success(f"Selected {len(selected_tables)} tables")
        else:
            st.sidebar.warning("No tables selected")
            
        return selected_tables
    except Exception as e:
        logger.error(f"Error in table selection: {str(e)}")
        st.sidebar.error("Error loading tables. Check your database connection.")
        return []

def main():
    try:
        # Verificar API key
        if not st.session_state.get('OPENAI_API_KEY'):
            st.error("OpenAI API Key not found. Please check your .env file.")
            return

        # Inicializar RAG
        initialize_rag_components()
        
        # Crear tabs principales
        tab1, tab2 = st.tabs(["Chat", "Debug Logs"])
        
        with tab1:
            # Header principal
            st.markdown(
                """
                <div style='text-align: center;'>
                    <h1>🤖 Quipu AI, your Data Analyst Assistant</h1>
                    <p style='font-size: 1.2em;'>Analyze your data with natural language queries | Analiza tus datos con preguntas en lenguaje natural</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Mostrar estado de conexión en sidebar
            connection_status = test_database_connection()
            if connection_status["success"]:
                st.sidebar.success("✔️ Connected to database")
                if connection_status["tables"]:
                    st.sidebar.info(f"Available tables: {len(connection_status['tables'])}")
            else:
                st.sidebar.error(f"❌ Connection error: {connection_status['error']}")
            
            # Selección de tablas en el sidebar
            selected_tables = display_table_selection()
            
            if not selected_tables:
                st.info("Please select at least one table from the sidebar to start querying.")
                return
            
            # Interfaz principal de consultas
            st.markdown("---")  # Separador visual
            display_query_interface()
            
            # Mostrar historial si existe
            if st.session_state.get('history', []):
                st.markdown("---")
                display_history()
        
        with tab2:
            display_debug_section()
        
        # Mostrar footer
        display_footer()
            
    except Exception as e:
        logger.error(f"Main application error: {str(e)}")
        st.error("An unexpected error occurred. Please check the logs for details.")

if __name__ == "__main__":
    main()