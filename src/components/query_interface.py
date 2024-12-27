# src/components/query_interface.py
import streamlit as st
import pandas as pd
from src.services.data_processing import handle_query_and_response
from src.components.visualization import create_visualization
from src.services.rag_service import process_query_with_rag
from pathlib import Path

def display_rag_status():
    """Display RAG status in the interface"""
    st.sidebar.markdown("### 🧠 Enhanced Features")
    
    rag_enabled = st.sidebar.toggle(
        "Enable document-enhanced responses",
        value=st.session_state.get('rag_enabled', True),
        help="Use additional context from documents in docs/ folder"
    )
    
    st.session_state['rag_enabled'] = rag_enabled
    
    if rag_enabled and st.session_state.get('rag_initialized'):
        st.sidebar.success("Document enhancement active")
        if 'docs_loaded' in st.session_state:
            with st.sidebar.expander("📚 Available Documents"):
                for doc in st.session_state['docs_loaded']:
                    st.write(f"- {Path(doc).name}")
    else:
        st.sidebar.info("Document enhancement disabled")

def display_quick_questions():
    """Display quick questions in sidebar"""
    st.sidebar.markdown("### ⚡ Quick Questions")
    
    quick_questions = [
        ("📊 Show total records", "Show me the total number of records in each table"),
        ("📈 Show data distribution", "Show me the distribution of incidents by type"),
        ("📅 Recent trends", "What are the trends in the last 6 months?")
    ]
    
    for label, question in quick_questions:
        if st.sidebar.button(label, use_container_width=True):
            st.session_state['current_question'] = question

def display_query_interface():
    """Display the main query interface"""
    # Initialize session states
    if 'current_question' not in st.session_state:
        st.session_state['current_question'] = ""
    
    # Show RAG status and quick questions in sidebar
    display_rag_status()
    st.sidebar.markdown("---")
    display_quick_questions()
    
    # Contenedor principal para el input y botón
    col1, col2 = st.columns([6,1])
    
    with col1:
        question = st.text_input(
            "",  # Removemos el label para mejor alineación
            value=st.session_state['current_question'],
            placeholder="Ask a question about your data...",
            label_visibility="collapsed"
        )
    
    with col2:
        ask_button = st.button("🔍 Ask", type="primary", use_container_width=True)
    
    # Process query if button is clicked or if we have a new quick question
    if ask_button or question != st.session_state['current_question']:
        if question:  # Solo procesar si hay una pregunta
            st.session_state['current_question'] = question
            process_query(question)

    # Process query if button is clicked or if we have a new quick question
    if ask_button or question != st.session_state['current_question']:
        if question:  # Solo procesar si hay una pregunta
            st.session_state['current_question'] = question
            process_query(question)

def handle_visualization(df: pd.DataFrame):
    """Create visualization with adjustable height"""
    create_visualization(df)

def process_query(question: str):
    """Process a query and display results"""
    with st.spinner('Processing your question...'):
        try:
            response = handle_query_and_response(question)
            
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
                                handle_visualization(df)
                        
                        # SQL Query section
                        if response.get('query'):
                            sql_expander = st.expander("🔍 SQL Query", expanded=False)
                            with sql_expander:
                                st.code(response.get('query', ''), language='sql')
                    
                    # Context section (when RAG is enabled)
                    if st.session_state.get('rag_enabled') and st.session_state.get('rag_initialized'):
                        if 'last_context' in st.session_state:
                            with st.expander("📚 Document Context Used", expanded=False):
                                for idx, ctx in enumerate(st.session_state['last_context'], 1):
                                    st.write(f"{idx}. {ctx[:200]}...")
                
                # Add to history
                if 'history' not in st.session_state:
                    st.session_state['history'] = []
                st.session_state['history'].append(response)
                
                # Separator for better visual organization
                st.markdown("---")
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            st.info("Please check your database connection and API keys.")