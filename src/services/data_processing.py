# src/services/data_processing.py

import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from src.utils.chatbot import generate_sql_chain, generate_response_chain
from src.services.state_management import store_debug_log
from src.services.rag_service import process_query_with_rag

def handle_query_and_response(question: str, selected_tables: List[str]) -> Dict[str, Any]:
    """Process a query and generate a response"""
    try:
        if st.session_state.get('rag_initialized') and st.session_state.get('rag_enabled', True):
            # Usar RAG solo si está habilitado
            rag_response = process_query_with_rag(question, selected_tables)
            query = rag_response['query']
            
            # Obtener respuesta completa usando el query mejorado por RAG
            full_chain = generate_response_chain(generate_sql_chain())
            full_response = full_chain.invoke({
                "question": question,
                "query": query,
                "selected_tables": selected_tables
            })
            
            # Añadir indicador RAG
            full_response = "🧠 " + full_response
            
            # Guardar contexto usado
            if 'context_used' in rag_response:
                st.session_state['last_context'] = rag_response['context_used']
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
        if 'DATA:' in full_response:
            try:
                main_response = full_response.split("DATA:")[0]
                data_str = full_response.split("DATA:")[1].strip()
                if data_str:
                    data_list = eval(data_str)
                    if isinstance(data_list, (list, tuple)) and len(data_list) > 0:
                        visualization_data = [
                            {"Categoría": str(cat), "Cantidad": float(count)}
                            for cat, count in data_list
                        ]
                full_response = main_response
            except Exception as e:
                logging.error(f"Error processing visualization data: {str(e)}")
        
        response_data = {
            'question': question,
            'query': query,
            'response': full_response,
            'visualization_data': visualization_data,
            'selected_tables': selected_tables
        }
        
        # Mantener el logging
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'full_response': full_response,
            'has_visualization': visualization_data is not None,
            'rag_enabled': st.session_state.get('rag_initialized', False),
            'selected_tables': selected_tables
        })
        
        return response_data
            
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        st.error(f"Error processing query: {str(e)}")
        return {}