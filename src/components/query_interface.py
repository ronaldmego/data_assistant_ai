# src/components/query_interface.py

import streamlit as st
import pandas as pd
from src.services.data_processing import handle_query_and_response
from src.components.visualization import create_visualization
from src.utils.database import get_all_tables
from typing import List

def display_table_selection() -> List[str]:
    """Display table selection interface and return selected tables"""
    try:
        tables = get_all_tables()
        if not tables:
            st.sidebar.error("No tables found in database.")
            return []
        
        st.sidebar.write("Select tables to query:")
        
        # Agregar botones para seleccionar/deseleccionar todo
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Select All"):
                for table in tables:
                    st.session_state[f"table_{table}"] = True
        with col2:
            if st.button("Deselect All"):
                for table in tables:
                    st.session_state[f"table_{table}"] = False
        
        selected_tables = []
        for table in tables:
            # Usar session_state para mantener el estado de las selecciones
            if f"table_{table}" not in st.session_state:
                st.session_state[f"table_{table}"] = False
                
            if st.sidebar.checkbox(
                f"{table}",
                value=st.session_state[f"table_{table}"],
                key=f"select_{table}"
            ):
                selected_tables.append(table)
                st.session_state[f"table_{table}"] = True
            else:
                st.session_state[f"table_{table}"] = False
                
        # Guardar las tablas seleccionadas en session_state
        st.session_state['selected_tables'] = selected_tables
                
        if selected_tables:
            st.sidebar.success(f"Selected {len(selected_tables)} tables")
        else:
            st.sidebar.warning("No tables selected")
            
        return selected_tables
    except Exception as e:
        st.sidebar.error(f"Error in table selection: {str(e)}")
        return []

def display_query_interface():
    """Display the main query interface"""
    # Initialize session states
    if 'current_question' not in st.session_state:
        st.session_state['current_question'] = ""
    
    # Obtener las tablas seleccionadas
    selected_tables = st.session_state.get('selected_tables', [])
    
    if not selected_tables:
        st.warning("Please select at least one table from the sidebar to start querying.")
        return
    
    # Mostrar las tablas seleccionadas en un expander
    with st.expander("Selected Tables", expanded=False):
        st.write(", ".join(selected_tables))
    
    # Contenedor principal para el input y botón
    col1, col2 = st.columns([6,1])
    
    with col1:
        question = st.text_input(
            "Question",  # Añadimos un label pero lo ocultamos
            value=st.session_state['current_question'],
            placeholder="Ask a question about your data...",
            label_visibility="collapsed"
        )
    
    with col2:
        ask_button = st.button("🔍 Ask", type="primary", use_container_width=True)
    
    # Process query if button is clicked or if we have a new quick question
    if ask_button or question != st.session_state['current_question']:
        if question and selected_tables:  # Solo procesar si hay una pregunta y tablas seleccionadas
            st.session_state['current_question'] = question
            process_query(question, selected_tables)

def process_query(question: str, selected_tables: List[str]):
    """Process a query and display results"""
    with st.spinner('Processing your question...'):
        try:
            response = handle_query_and_response(question, selected_tables)
            
            if response:
                # Main response container
                response_container = st.container()
                with response_container:
                    # Answer section
                    st.markdown("### Answer")
                    st.write(response.get('response', ''))
                    
                    # Results section
                    results_container = st.container()
                    with results_container:
                        # Visualization section
                        if response.get('visualization_data'):
                            viz_expander = st.expander("📊 Data Visualization", expanded=True)
                            with viz_expander:
                                df = pd.DataFrame(response['visualization_data'])
                                create_visualization(df)
                        
                        # SQL Query section
                        if response.get('query'):
                            sql_expander = st.expander("🔍 SQL Query", expanded=False)
                            with sql_expander:
                                st.code(response.get('query', ''), language='sql')

                        # RAG Context section
                        if response.get('rag_context'):
                            rag_expander = st.expander("📚 Documents Used for Analysis", expanded=False)
                            with rag_expander:
                                st.markdown("The following document excerpts were used to enhance the analysis:")
                                for idx, ctx in enumerate(response['rag_context'], 1):
                                    st.markdown(f"**Document {idx}:**")
                                    st.markdown(f"```\n{ctx[:300]}...\n```")
                                    st.markdown("---")
                
                # Add to history
                if 'history' not in st.session_state:
                    st.session_state['history'] = []
                st.session_state['history'].append(response)
                
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            st.info("Please check your database connection and API keys.")