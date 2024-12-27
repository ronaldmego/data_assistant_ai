# src/services/data_processing.py
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from src.utils.chatbot import process_user_query, generate_sql_chain, generate_response_chain
from src.services.state_management import store_debug_log
from src.services.rag_service import process_query_with_rag

logger = logging.getLogger(__name__)

def parse_numerical_data(text: str) -> Optional[pd.DataFrame]:
    """Parse numerical data from response text"""
    try:
        if 'DATA:' in text:
            data_str = text.split('DATA:')[1].split('\n')[0].strip()
            try:
                data_list = eval(data_str)
                if data_list:
                    return pd.DataFrame(data_list, columns=["Categoría", "Cantidad"])
            except:
                logger.error("Error evaluating data string")
                return None
        return None
    except Exception as e:
        logger.error(f"Error parsing numerical data: {str(e)}")
        return None

def handle_query_and_response(question: str) -> Dict[str, Any]:
    """Process a query and generate a response"""
    try:
        if not st.session_state.get('selected_tables'):
            return {
                'question': question,
                'response': "Please select at least one table before querying.",
                'query': None,
                'visualization_data': None
            }

        if st.session_state.get('rag_initialized') and st.session_state.get('rag_enabled', True):
            # Use RAG if enabled
            rag_response = process_query_with_rag(question)
            if 'error' in rag_response:
                logger.error(f"RAG error: {rag_response['error']}")
                return {
                    'question': question,
                    'response': f"Error processing query: {rag_response['error']}",
                    'query': None,
                    'visualization_data': None
                }
            query = rag_response['query']
            
            # Get full response using RAG-enhanced query
            full_chain = generate_response_chain(generate_sql_chain())
            full_response = full_chain.invoke({
                "question": question,
                "query": query
            })
            
            # Add RAG indicator
            full_response = "🧠 " + str(full_response)
            
            # Save used context
            if 'context_used' in rag_response:
                st.session_state['last_context'] = rag_response['context_used']
        else:
            # Original process without RAG
            sql_chain = generate_sql_chain()
            full_chain = generate_response_chain(sql_chain)
            query = sql_chain.invoke({"question": question})
            full_response = full_chain.invoke({
                "question": question,
                "query": query
            })

        # Process visualization
        visualization_data = None
        df = parse_numerical_data(full_response)
        if df is not None:
            visualization_data = df.to_dict('records')
        
        # Prepare complete response
        response_data = {
            'question': question,
            'query': query,
            'response': full_response,
            'visualization_data': visualization_data
        }
        
        # Store debug log
        store_debug_log({
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'full_response': full_response,
            'has_visualization': visualization_data is not None,
            'rag_enabled': st.session_state.get('rag_initialized', False),
            'selected_tables': st.session_state.get('selected_tables', [])
        })
        
        return response_data
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'question': question,
            'response': f"Error processing query: {str(e)}",
            'query': None,
            'visualization_data': None
        }