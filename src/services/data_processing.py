# src/services/data_processing.py
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from src.utils.chatbot import process_user_query, generate_sql_chain, generate_response_chain
from src.services.state_management import store_debug_log

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
        sql_chain = generate_sql_chain()
        full_chain = generate_response_chain(sql_chain)
        
        # Primero obtener el SQL query
        query = sql_chain.invoke({"question": question})
        
        # Luego obtener la respuesta completa
        full_response = full_chain.invoke({
            "question": question,
            "query": query
        })
        
        # Procesar la respuesta para extraer los datos de visualización
        visualization_data = None
        df = parse_numerical_data(full_response)
        if df is not None:
            visualization_data = df.to_dict('records')
        
        # Guardar en el historial con todos los componentes
        response_data = {
            'question': question,
            'query': query,
            'response': full_response,
            'visualization_data': visualization_data
        }
        
        # Almacenar información de debug
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'full_response': full_response,
            'has_visualization': visualization_data is not None
        })
        
        return response_data
            
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        st.error(f"Error processing query: {str(e)}")
        return {}