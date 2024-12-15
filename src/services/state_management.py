# src/services/state_management.py
import streamlit as st

def initialize_session_state():
    """Initialize session state variables"""
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'debug_logs' not in st.session_state:
        st.session_state['debug_logs'] = []

def store_debug_log(data):
    """Store debug information"""
    st.session_state['debug_logs'].append(data)