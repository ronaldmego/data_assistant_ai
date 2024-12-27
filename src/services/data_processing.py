# src/services/data_processing.py
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from src.utils.chatbot import generate_sql_chain, generate_response_chain
from src.services.state_management import store_debug_log
from src.services.rag_service import process_query_with_rag

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

# src/services/data_processing.py

def handle_query_and_response(question: str, selected_tables: List[str]) -> Dict[str, Any]:
    """Process a query and generate a response"""
    try:
        if 'debug_logs' not in st.session_state:
            st.session_state['debug_logs'] = []
            
        if st.session_state.get('rag_initialized') and st.session_state.get('rag_enabled', True):
            # Usar RAG si está inicializado y habilitado
            rag_response = process_query_with_rag(question, selected_tables)
            query = rag_response.get('query', '')
            context_used = rag_response.get('context_used', [])
            st.session_state['last_context'] = context_used
            
            full_chain = generate_response_chain(generate_sql_chain())
            full_response = full_chain.invoke({
                "question": question,
                "query": query,
                "selected_tables": selected_tables
            })
            full_response = "🧠 " + str(full_response)
            
        else:
            # Proceso original sin RAG
            sql_chain = generate_sql_chain()
            full_chain = generate_response_chain(sql_chain)
            query = sql_chain.invoke({
                "question": question,
                "selected_tables": selected_tables
            })
            full_response = full_chain.invoke({
                "question": question,
                "query": query,
                "selected_tables": selected_tables
            })

        # Procesar visualización
        visualization_data = None
        if isinstance(full_response, str) and 'DATA:' in full_response:
            try:
                parts = full_response.split("DATA:")
                if len(parts) >= 2:
                    main_response = parts[0]
                    data_str = parts[1].strip()
                    if data_str:
                        try:
                            data_list = eval(data_str)
                            if isinstance(data_list, (list, tuple)) and len(data_list) > 0:
                                visualization_data = [
                                    {"Categoría": str(cat), "Cantidad": float(count)}
                                    for cat, count in data_list
                                ]
                            full_response = main_response
                        except Exception as e:
                            logger.error(f"Error parsing data list: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing visualization data: {str(e)}")
        
        response_data = {
            'question': question,
            'query': query,
            'response': full_response,
            'visualization_data': visualization_data,
            'selected_tables': selected_tables,
            'rag_context': st.session_state.get('last_context', [])
        }
        
        # Almacenar en debug_logs
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'full_response': full_response,
            'has_visualization': visualization_data is not None,
            'rag_enabled': st.session_state.get('rag_initialized', False),
            'selected_tables': selected_tables,
            'rag_context': st.session_state.get('last_context', [])
        })
        
        return response_data
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        error_response = {
            'question': question,
            'response': f"Lo siento, hubo un error al procesar tu consulta: {str(e)}",
            'query': None,
            'visualization_data': None,
            'selected_tables': selected_tables,
            'rag_context': []
        }
        
        # Almacenar error en debug_logs
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'error': str(e),
            'selected_tables': selected_tables
        })
        
        return error_response