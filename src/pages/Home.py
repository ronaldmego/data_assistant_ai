# src/pages/Home.py
import sys
from pathlib import Path
import streamlit as st
import logging
import os

# Añadir el directorio raíz al path de manera robusta
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# Importar config
from config.config import OPENAI_API_KEY, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE

# Configuración inicial de la página
st.set_page_config(
    page_title="🤖 Quipu AI, your Data Analyst Assistant",
    page_icon="🤖",
    layout="wide"
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
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
    if 'selected_tables' not in st.session_state:
        st.session_state['selected_tables'] = []
    
    # LLM configuration
    if 'llm_provider' not in st.session_state:
        st.session_state['llm_provider'] = 'ollama'  # Default to ollama
    if 'llm_model_name' not in st.session_state:
        st.session_state['llm_model_name'] = 'llama3:8b-instruct-q8_0'  # Default model
    if 'llm_temperature' not in st.session_state:
        st.session_state['llm_temperature'] = 0.7

try:
    # Import components
    from src.utils.database import get_all_tables, test_database_connection
    from src.utils.chatbot import generate_sql_chain, generate_response_chain
    from src.services.data_processing import handle_query_and_response
    from src.services.rag_service import initialize_rag_components
    from src.components.debug_panel import display_debug_section
    from src.components.history_view import display_history
    from src.components.query_interface import display_query_interface, display_table_selection, display_model_settings
    from src.layouts.footer import display_footer
    from src.layouts.header import display_header

    logger.info("All components loaded successfully")
except Exception as e:
    logger.error(f"Failed to import required components: {str(e)}")
    st.error(f"Failed to import required components: {str(e)}")
    st.stop()

def main():
    try:
        # Inicializar session state
        initialize_session_state()
        
        # Header principal
        display_header()
        
        # Sidebar settings
        st.sidebar.markdown("---")
        
        # Model settings section
        display_model_settings()
        st.sidebar.markdown("---")
        
        # Verificar API key si se usa OpenAI
        if st.session_state.get('llm_provider') == 'openai':
            if not st.session_state.get('OPENAI_API_KEY'):
                st.sidebar.error("⚠️ OpenAI API Key not found. Please check your .env file or switch to Ollama.")
                return
        
        # Inicializar RAG
        initialize_rag_components()
        
        # Database connection status
        connection_status = test_database_connection()
        if connection_status["success"]:
            st.sidebar.success("✔️ Connected to database")
            if connection_status["tables"]:
                st.sidebar.info(f"Available tables: {len(connection_status['tables'])}")
        else:
            st.sidebar.error(f"❌ Connection error: {connection_status['error']}")
            return
        
        # Table selection
        selected_tables = display_table_selection()
        
        # Main content tabs
        tab1, tab2 = st.tabs(["Chat", "Debug Logs"])
        
        with tab1:
            # Mostrar la interfaz principal solo si hay tablas seleccionadas
            if selected_tables:
                st.session_state['selected_tables'] = selected_tables
                st.markdown("---")  # Separador visual
                display_query_interface()
                
                # Mostrar historial si existe
                if st.session_state.get('history', []):
                    st.markdown("---")
                    display_history()
            else:
                st.info("Please select at least one table from the sidebar to start querying.")
        
        with tab2:
            display_debug_section()
        
        # Footer
        display_footer()
            
    except Exception as e:
        logger.error(f"Main application error: {str(e)}")
        st.error("An unexpected error occurred. Please check the logs for details.")

if __name__ == "__main__":
    main()