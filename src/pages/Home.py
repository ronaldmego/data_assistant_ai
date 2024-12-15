# streamlit run src/pages/Home.py
import sys
from pathlib import Path
import streamlit as st
import logging

# Configuración inicial de la página
st.set_page_config(
    page_title="🤖 Quipu AI, your Data Analyst Assistant",
    page_icon="🤖",
    layout="wide"
)

# Añadir el directorio raíz al path de manera robusta
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

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

# mostrar mensajes de diagnóstico
st.write("Starting application...")

# Importar todas las dependencias
try:
    # Importar utilidades primero ya que otros módulos dependen de ellas
    from src.utils.database import get_all_tables, test_database_connection
    from src.utils.chatbot import generate_sql_chain, generate_response_chain

    # Importar servicios
    from src.services.state_management import initialize_session_state
    from src.services.data_processing import handle_query_and_response, parse_numerical_data

    # Importar componentes
    from src.components.debug_panel import display_debug_section
    from src.components.history_view import display_history
    from src.components.query_interface import display_query_interface
    from src.components.visualization import create_visualization

    # Importar layouts
    from src.layouts.footer import display_footer
    from src.layouts.header import display_header, display_subheader

    st.write("All components loaded successfully")
except Exception as e:
    st.error(f"Failed to import required components: {str(e)}")
    logger.error(f"Import error: {str(e)}")
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
        initialize_session_state()
        
        # Crear tabs principales
        tab1, tab2 = st.tabs(["Chat", "Debug Logs"])
        
        with tab1:
            # Mostrar header con estado de conexión
            display_header(show_connection_status=True)
            
            # Selección de tablas en el sidebar
            selected_tables = display_table_selection()
            
            if not selected_tables:
                st.info("Please select at least one table from the sidebar to start querying.")
                return
            
            # Interfaz principal de consultas
            display_subheader(
                "Ask Questions About Your Data | Haz preguntas sobre tus datos",
                "Use natural language to query your database | Utiliza un lenguaje natural para consultar tu base de datos"
            )
            
            # Mostrar interfaz de consultas
            display_query_interface()
            
            # Mostrar historial si existe
            if st.session_state.get('history', []):
                st.markdown("---")
                display_subheader("Previous Queries", "History of your interactions")
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