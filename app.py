import streamlit as st
from chatbot import generate_sql_chain, generate_response_chain
from database import get_all_tables, get_ignored_tables
from typing import List, Optional, Dict
import logging
import json
import pandas as pd
import matplotlib.pyplot as plt

def initialize_session_state():
    """Initialize session state variables"""
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'debug_logs' not in st.session_state:
        st.session_state['debug_logs'] = []

def extract_clean_response(response):
    """Extract just the content from the response without any metadata"""
    try:
        # Si es string y contiene el formato esperado de contenido
        if isinstance(response, str):
            if 'content=' in response:
                import re
                # Usar regex para extraer el contenido entre comillas
                match = re.search(r"content='([^']*)'", response)
                if match:
                    return match.group(1)
            return response
            
        # Si es diccionario
        if isinstance(response, dict):
            return response.get('content', str(response))
            
        return str(response)
    except Exception as e:
        return str(response)

def store_debug_log(data):
    """Store debug information"""
    st.session_state['debug_logs'].append(data)

def display_table_selection():
    """Display table selection interface"""
    st.sidebar.header("Database Tables")
    
    all_tables = get_all_tables()
    ignored_tables = get_ignored_tables()
    
    if not all_tables:
        st.sidebar.error("No tables found in the database.")
        return []
    
    available_tables = [table for table in all_tables if table not in ignored_tables]
    
    if not available_tables:
        st.sidebar.warning("All tables are currently ignored.")
        return []
    
    selected_tables = []
    st.sidebar.write("Select tables to query:")
    
    for table in available_tables:
        if st.sidebar.checkbox(f"{table}", value=True, key=f"table_{table}"):
            selected_tables.append(table)
            
    if selected_tables:
        st.sidebar.success(f"Selected {len(selected_tables)} tables")
    else:
        st.sidebar.warning("No tables selected")
        
    return selected_tables

def display_history():
    """Display query history"""
    st.header("Conversation History")
    
    for idx, item in enumerate(reversed(st.session_state['history']), 1):
        with st.container():
            st.markdown(f"**Q{idx}:** {item['question']}")
            st.markdown(f"**A:** {item['response']}")
            
            # SQL Query siempre visible y con ancho completo
            st.markdown("**SQL Query:**")
            st.code(item['query'], language='sql')
            
            # Agregar botón de visualización si hay datos disponibles
            if item.get('visualization_data'):
                if st.button(f"📊 Ver Gráfico {idx}"):
                    df = pd.DataFrame(item['visualization_data'])
                    create_visualization(df)
            
            st.divider()

def handle_query_and_response(question: str):
    """Handle both query generation and execution in one step"""
    if not question.strip():
        st.warning("Please enter a question first.")
        return

    with st.spinner('Processing your question...'):
        try:
            # Generar y ejecutar la consulta
            sql_chain = generate_sql_chain()
            full_chain = generate_response_chain(sql_chain)
            
            # Obtener la consulta SQL para el registro
            query = sql_chain.invoke({"question": question})
            
            # Obtener la respuesta final
            full_response = full_chain.invoke({
                "question": question,
                "query": query
            })
            
            # Extraer solo la respuesta limpia
            clean_response = extract_clean_response(full_response)
            
            # Guardar la respuesta completa en los logs de debug
            store_debug_log({
                'timestamp': st.session_state.get('timestamp'),
                'full_response': full_response
            })
            
            # Mostrar la respuesta limpia
            st.markdown("**Answer:**")
            st.write(clean_response)
            
            # Mostrar la consulta SQL
            st.markdown("**SQL Query:**")
            st.code(query, language='sql')
            
            # Verificar si los datos pueden ser visualizados
            df = parse_numerical_data(clean_response)
            if df is not None:
                if st.button("📊 Visualizar Datos"):
                    st.markdown("**Visualización:**")
                    create_visualization(df)
            
            # Guardar en el historial
            st.session_state['history'].append({
                'question': question,
                'query': query,
                'response': clean_response,
                'visualization_data': df.to_dict('records') if df is not None else None
            })
            
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")

def display_debug_section():
    """Display debug information in a separate section"""
    st.header("Debug Information")
    if st.session_state['debug_logs']:
        for idx, log in enumerate(st.session_state['debug_logs'], 1):
            with st.expander(f"Debug Log {idx}", expanded=False):
                st.json(log)
    else:
        st.write("No debug logs available")

def parse_numerical_data(text: str) -> Optional[pd.DataFrame]:
    """
    Analiza el texto de la respuesta para extraer datos numéricos estructurados
    """
    try:
        # Buscar el bloque de datos estructurados
        if 'DATA_START' in text and 'DATA_END' in text:
            # Extraer el bloque de datos
            data_block = text.split('DATA_START')[1].split('DATA_END')[0].strip()
            
            # Procesar cada línea de datos
            data = []
            for line in data_block.split('\n'):
                line = line.strip()
                if line:
                    # Extraer categoría y cantidad
                    category = line.split('Category:')[1].split(',')[0].strip()
                    count = float(line.split('Count:')[1].strip().replace(',', ''))
                    data.append({
                        "Categoría": category,
                        "Cantidad": count
                    })
            
            if len(data) > 1:
                return pd.DataFrame(data)
        
        return None
    except Exception as e:
        st.error(f"Error parsing data: {str(e)}")
        return None

def create_visualization(df: pd.DataFrame):
    """
    Crea una visualización usando matplotlib y seaborn
    """
    import seaborn as sns
    sns.set_style("whitegrid")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Crear el gráfico de barras con seaborn
    sns.barplot(data=df, x='Categoría', y='Cantidad', ax=ax)
    
    ax.set_title('Distribución de Datos', pad=20)
    ax.set_xlabel('Categoría')
    ax.set_ylabel('Cantidad')
    
    if len(df) > 4:
        plt.xticks(rotation=45, ha='right')
    
    # Agregar etiquetas de valores sobre las barras
    for i in ax.containers:
        ax.bar_label(i, fmt='%.0f')
    
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def main():
    st.set_page_config(
        page_title="Open Source - AI Data Analyst Assistant",
        page_icon="🤖",
        layout="wide"
    )
    
    initialize_session_state()
    
    # Configurar las tabs
    tab1, tab2 = st.tabs(["Chat", "Debug Logs"])
    
    with tab1:
        # Mostrar estado de la conexión
        try:
            tables = get_all_tables()
            if tables:
                st.sidebar.success("✔️ Connected to database")
            else:
                st.sidebar.error("❌ No tables found in database")
        except Exception as e:
            st.sidebar.error(f"❌ Database connection error: {str(e)}")
            return
        
        selected_tables = display_table_selection()
        
        if not selected_tables:
            st.info("Please select at least one table from the sidebar to start querying.")
            return
        
        st.title("SQL Database Assistant")
        
        # Interfaz de chat simplificada
        user_question = st.text_input(
            "Ask a question about your data:",
            placeholder="e.g., How many records are there in total?"
        )
        
        if st.button("Ask"):
            handle_query_and_response(user_question)
            st.divider()
        
        # Mostrar historial
        if st.session_state.get('history', []):
            display_history()
    
    with tab2:
        display_debug_section()

if __name__ == "__main__":
    main()