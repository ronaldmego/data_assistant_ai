# src/pages/Home.py
import sys
from pathlib import Path
import streamlit as st
import logging
import os

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

# Importaciones adicionales
from src.utils.database import get_all_tables, test_database_connection, get_table_info, get_table_columns
from src.components.debug_panel import display_debug_section
from src.components.history_view import display_history
from src.components.query_interface import display_query_interface
from src.layouts.footer import display_footer
from src.layouts.header import display_header
from src.services.rag_service import initialize_rag_components

def initialize_session_state():
    """Initialize all session state variables"""
    if 'initialized' not in st.session_state:
        logger.info("Initializing session state...")
        
        # Load environment variables
        if not OPENAI_API_KEY:
            st.error("""
            ⚠️ OpenAI API Key not found!
            
            Please follow these steps:
            1. Create a .env file in the project root
            2. Add your OpenAI API key: OPENAI_API_KEY=your_key_here
            3. Add other required configurations (check .env.example)
            4. Restart the application
            """)
            st.stop()
            
        # Initialize other session state variables
        initial_states = {
            'history': [],
            'debug_logs': [],
            'selected_tables': [],
            'selected_all': False,
            'OPENAI_API_KEY': OPENAI_API_KEY,
            'DB_CONFIG': {
                'user': MYSQL_USER,
                'password': MYSQL_PASSWORD,
                'host': MYSQL_HOST,
                'database': MYSQL_DATABASE
            },
            'initialized': True
        }
        
        for key, value in initial_states.items():
            if key not in st.session_state:
                st.session_state[key] = value

def display_table_selection():
    """Display table selection interface"""
    try:
        # Asegurarnos de que table_info está en el session state
        if 'table_info' not in st.session_state:
            st.session_state['table_info'] = get_table_info()
            
        table_info = st.session_state.get('table_info', {})
        if not table_info:
            st.sidebar.error("No tables found in database.")
            return []
        
        st.sidebar.write("### 📊 Table Selection")
        
        # Agregar selector de período
        st.sidebar.write("#### 📅 Time Period")
        all_tables = sorted(list(table_info.keys()))
        
        # Extraer años y meses únicos
        years = sorted(list(set([table[-6:-2] for table in all_tables])))
        
        selected_year = st.sidebar.selectbox("Select Year", years, index=len(years)-1)
        
        # Filtrar tablas por año seleccionado
        year_tables = [t for t in all_tables if selected_year in t]
        months = sorted(list(set([table[-2:] for table in year_tables])))
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_month = st.selectbox("From", months, index=0)
        with col2:
            end_month = st.selectbox("To", months, index=len(months)-1)
            
        # Filtrar tablas por período seleccionado
        selected_tables = [
            table for table in year_tables 
            if start_month <= table[-2:] <= end_month
        ]
        
        # Mostrar información de tablas seleccionadas
        if selected_tables:
            total_rows = sum(table_info.get(table, 0) for table in selected_tables)
            total_columns = sum(len(get_table_columns(table)) for table in selected_tables)
            estimated_tokens = total_columns * len(selected_tables) * 50
            
            # Información de selección
            st.sidebar.success(
                f"📊 Selected {len(selected_tables)} tables\n"
                f"📈 Total rows: {total_rows:,}\n"
                f"🔢 Total columns: {total_columns}"
            )
            
            # Warning de tokens si es necesario
            if estimated_tokens > 4000:
                st.sidebar.warning(
                    f"⚠️ Token Limit Warning\n\n"
                    f"Estimated tokens: {estimated_tokens:,}\n"
                    "Try selecting fewer months or tables.",
                    icon="⚠️"
                )
            
            # Mostrar tablas seleccionadas en un expander
            with st.sidebar.expander("📋 Selected Tables", expanded=False):
                for table in selected_tables:
                    st.write(f"- {table} ({table_info.get(table, 0):,} rows)")
        else:
            st.sidebar.warning("No tables selected for the specified period")
        
        # Guardar en session state
        st.session_state['selected_tables'] = selected_tables
        
        return selected_tables
    
    except Exception as e:
        logger.error(f"Error in table selection: {str(e)}")
        st.sidebar.error("Error loading tables. Check your database connection.")
        return []

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
                if connection_status.get("tables"):
                    st.sidebar.info(f"Available tables: {len(connection_status['tables'])}")
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