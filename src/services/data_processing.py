# src/services/data_processing.py
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from src.utils.chatbot import process_user_query, generate_sql_chain, generate_response_chain
from src.services.state_management import store_debug_log
from src.services.rag_service import process_query_with_rag  # RAG

def parse_numerical_data(text: str) -> Optional[pd.DataFrame]:
    """Parse numerical data from response text"""
    try:
        if 'DATA:' in text:
            # Extraer el string entre DATA: y el final o siguiente salto de línea
            data_str = text.split('DATA:')[1].split('\n')[0].strip()
            
            try:
                # Evaluar el string como lista de tuplas
                data_list = eval(data_str)
                
                # Convertir a DataFrame
                if data_list:
                    return pd.DataFrame(data_list, columns=["Categoría", "Cantidad"])
            except:
                logging.error("Error evaluating data string")
                return None
        
        return None
    except Exception as e:
        logging.error(f"Error parsing numerical data: {str(e)}")
        return None

def handle_query_and_response(question: str) -> Dict[str, Any]:
    """Process a query and generate a response"""
    try:
        if st.session_state.get('rag_initialized') and st.session_state.get('rag_enabled', True):
            # Usar RAG solo si está habilitado
            rag_response = process_query_with_rag(question)
            query = rag_response['query']
            
            # Obtener respuesta completa usando el query mejorado por RAG
            full_chain = generate_response_chain(generate_sql_chain())
            full_response = full_chain.invoke({
                "question": question,
                "query": query
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
            query = sql_chain.invoke({"question": question})
            full_response = full_chain.invoke({
                "question": question,
                "query": query
            })

        # Procesar visualización (mantener tu código existente)
        visualization_data = None
        df = parse_numerical_data(full_response)
        if df is not None:
            visualization_data = df.to_dict('records')
        
        # Preparar respuesta completa
        response_data = {
            'question': question,
            'query': query,
            'response': full_response,
            'visualization_data': visualization_data
        }
        
        # Mantener el logging (tu código existente)
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'full_response': full_response,
            'has_visualization': visualization_data is not None,
            'rag_enabled': st.session_state.get('rag_initialized', False)
        })
        
        return response_data
            
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        st.error(f"Error processing query: {str(e)}")
        return {}