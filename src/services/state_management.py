# src/services/state_management.py
import streamlit as st

def initialize_session_state():
    """Initialize session state variables"""
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'debug_logs' not in st.session_state:
        st.session_state['debug_logs'] = []
    if 'OPENAI_API_KEY' not in st.session_state:
        st.session_state['OPENAI_API_KEY'] = None
    if 'selected_tables' not in st.session_state:
        st.session_state['selected_tables'] = []
        
    # LLM configuration
    if 'llm_provider' not in st.session_state:
        st.session_state['llm_provider'] = 'ollama'  # Cambio a ollama por defecto
    if 'llm_model_name' not in st.session_state:
        st.session_state['llm_model_name'] = 'llama3:8b-instruct-q8_0'
    if 'llm_temperature' not in st.session_state:
        st.session_state['llm_temperature'] = 0.7

def store_debug_log(data):
    """Store debug information"""
    if 'debug_logs' not in st.session_state:
        st.session_state['debug_logs'] = []
    st.session_state['debug_logs'].append(data)