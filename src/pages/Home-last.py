# src/pages/Home.py
import sys
from pathlib import Path
import streamlit as st
import logging
import os
from typing import List, Dict, Optional

# Añadir el directorio raíz al path de manera robusta
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# Configuración inicial de la página
st.set_page_config(
    page_title="🤖 Quipu AI, your Data Analyst Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# AHORA sí podemos importar módulos desde src
from src.utils.logging_config import setup_logging
logger = setup_logging()

# Importar config
from config.config import OPENAI_API_KEY, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_table_columns(table_name: str) -> List[str]:
    """Get columns for a specific table"""
    try:
        from src.utils.database import run_query
        query = f"SHOW COLUMNS FROM {table_name}"
        result = run_query(query)
        return [row[0] for row in result]
    except Exception as e:
        logger.error(f"Error getting columns for table {table_name}: {str(e)}")
        return []

@st.cache_data(ttl=300)
def get_table_info() -> Dict[str, int]:
    """Get table information with row counts"""
    try:
        from src.utils.database import run_query, get_all_tables
        tables = get_all_tables()
        info = {}
        
        for table in tables:
            try:
                # Usar parámetros para evitar problemas de SQL injection
                query = f"SELECT COUNT(*) as count FROM `{table}`"
                result = run_query(query)
                # Asegurarnos de que tenemos un resultado y es un número
                count = int(result[0][0]) if result and result[0] else 0
                info[table] = count
            except Exception as e:
                logger.warning(f"Error getting count for table {table}: {str(e)}")
                info[table] = 0
                
        return info
    except Exception as e:
        logger.error(f"Error getting table info: {str(e)}")
        return {}

def initialize_session_state():
    """Initialize all session state variables"""
    if not st.session_state.get('initialized'):
        logger.info("Initializing session state...")
        initial_states = {
            'history': [],
            'debug_logs': [],
            'OPENAI_API_KEY': OPENAI_API_KEY,
            'DB_CONFIG': {
                'user': MYSQL_USER,
                'password': MYSQL_PASSWORD,
                'host': MYSQL_HOST,
                'database': MYSQL_DATABASE
            },
            'selected_tables': [],
            'selected_all': False,
            'table_info': get_table_info(),
            'initialized': True
        }
        
        for key, value in initial_states.items():
            if key not in st.session_state:
                st.session_state[key] = value

def display_table_selection():
    """Display table selection interface"""
    try:
        table_info = st.session_state.get('table_info', {})
        if not table_info:
            st.sidebar.error("No tables found in database.")
            return []
        
        st.sidebar.write("### 📊 Table Selection")
        
        # Agregar botones de selección
        col1, col2 = st.sidebar.columns(2)
        if col1.button("Select All", use_container_width=True):
            st.session_state['selected_all'] = True
        if col2.button("Deselect All", use_container_width=True):
            st.session_state['selected_all'] = False
        
        # Búsqueda de tablas
        search = st.sidebar.text_input("🔍 Search tables:", "")
        
        # Filtrar y ordenar tablas
        filtered_tables = [
            table for table in table_info.keys() 
            if search.lower() in table.lower()
        ]
        filtered_tables.sort()
        
        selected_tables = []
        total_rows = 0
        
        # Crear contenedor scrolleable
        with st.sidebar.container():
            for table in filtered_tables:
                row_count = table_info[table]
                if st.checkbox(
                    f"{table} ({row_count:,} rows)",
                    value=st.session_state.get('selected_all', False),
                    key=f"table_{table}"
                ):
                    selected_tables.append(table)
                    total_rows += row_count
        
        # Mostrar estadísticas
        if selected_tables:
            st.sidebar.success(
                f"Selected {len(selected_tables)}/{len(table_info)} tables\n"
                f"Total rows: {total_rows:,}"
            )
            
            # Estimación de tokens
            total_columns = sum(len(get_table_columns(table)) for table in selected_tables)
            estimated_tokens = total_columns * len(selected_tables) * 50  # estimación aproximada
            
            if estimated_tokens > 4000:
                st.sidebar.warning(
                    "⚠️ **Token Limit Warning**\n\n"
                    f"Estimated tokens: {estimated_tokens:,}\n"
                    "Consider reducing selected tables.",
                    icon="⚠️"
                )
        else:
            st.sidebar.warning("No tables selected")
        
        # Guardar en session state
        st.session_state['selected_tables'] = selected_tables
        
        return selected_tables
    
    except Exception as e:
        logger.error(f"Error in table selection: {str(e)}")
        st.sidebar.error("Error loading tables. Check your database connection.")
        return []

try:
    # Import components
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

def main():
    try:
        # Initialize
        initialize_session_state()
        
        # Verificar API key
        if not st.session_state.get('OPENAI_API_KEY'):
            st.error("OpenAI API Key not found. Please check your .env file.")
            return

        # Inicializar RAG
        if not st.session_state.get('rag_initialized', False):
            with st.spinner("Initializing AI components..."):
                initialize_rag_components()
        
        # Crear tabs principales
        tab1, tab2 = st.tabs(["💬 Chat", "🔧 Debug"])
        
        with tab1:
            # Header principal
            st.markdown(
                """
                <div style='text-align: center;'>
                    <h1>🤖 Quipu AI, your Data Analyst Assistant</h1>
                    <p style='font-size: 1.2em;'>Analyze your data with natural language queries | 
                    Analiza tus datos con preguntas en lenguaje natural</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Mostrar estado de conexión en sidebar
            connection_status = test_database_connection()
            if connection_status["success"]:
                st.sidebar.success("✔️ Connected to database")
            else:
                st.sidebar.error(f"❌ Connection error: {connection_status['error']}")
                return
            
            # Selección de tablas en el sidebar
            selected_tables = display_table_selection()
            
            if not selected_tables:
                st.info("👈 Please select at least one table from the sidebar to start querying.")
                return
            
            # Interfaz principal de consultas
            st.markdown("---")
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