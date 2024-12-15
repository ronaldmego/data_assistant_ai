# src/components/query_interface.py
import streamlit as st
import pandas as pd
from src.services.data_processing import handle_query_and_response
from src.components.visualization import create_visualization

def display_query_interface():
    """Display the main query interface"""
    user_question = st.text_input(
        "Ask a question about your data: | Haz preguntas sobre tu data:",
        placeholder="e.g., How many records are there in total? | ¿Cuántos registros hay en total?"
    )
    
    if st.button("Ask"):
        if not user_question.strip():
            st.warning("Please enter a question first.")
            return

        with st.spinner('Processing your question...'):
            # Obtener respuesta
            response = handle_query_and_response(user_question)
            
            if response:
                # Mostrar la respuesta
                st.markdown("**Answer:**")
                st.write(response.get('response', ''))
                
                # Mostrar la consulta SQL si existe
                if response.get('query'):
                    st.markdown("**SQL Query:**")
                    st.code(response.get('query', ''), language='sql')
                
                # Verificar si hay datos para visualizar y mostrar el botón
                if response.get('visualization_data'):
                    if st.button("📊 Visualizar Datos"):
                        st.markdown("**Visualization:**")
                        df = pd.DataFrame(response['visualization_data'])
                        create_visualization(df)
                
                # Guardar en el historial
                if 'history' not in st.session_state:
                    st.session_state['history'] = []
                
                st.session_state['history'].append(response)