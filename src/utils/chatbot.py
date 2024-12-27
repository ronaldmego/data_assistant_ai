# src/utils/chatbot.py
import streamlit as st
from typing import Dict, List, Union, Any, Tuple, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
import logging
from .database import get_schema, run_query, get_all_tables
from config.config import OPENAI_API_KEY
import pandas as pd
from .schema_utils import analyze_table_name_pattern, get_relevant_tables, chunk_schema

logger = logging.getLogger(__name__)

# Verificar que la API key existe
if not OPENAI_API_KEY:
    logger.error("OpenAI API key not found in environment variables")
    raise ValueError("OpenAI API key is required")

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    openai_api_key=OPENAI_API_KEY
)

def filter_schema_for_tables(schema: str, table_names: List[str]) -> str:
    """Filtra el esquema para incluir solo las tablas especificadas"""
    if not schema or not table_names:
        logger.warning("Empty schema or table names provided")
        return ""
        
    try:
        filtered_parts = []
        current_table = ""
        current_content = []
        
        for line in schema.split('\n'):
            if line.startswith('CREATE TABLE'):
                if current_table and current_table in table_names:
                    filtered_parts.extend(current_content)
                try:
                    current_table = line.split('`')[1] if '`' in line else line.split(' ')[2]
                except IndexError:
                    logger.warning(f"Could not parse table name from line: {line}")
                    continue
                current_content = [line]
            elif line.startswith(');'):
                current_content.append(line)
                if current_table in table_names:
                    filtered_parts.extend(current_content)
                current_table = ""
                current_content = []
            elif current_table:
                current_content.append(line)
        
        if current_table and current_table in table_names:
            filtered_parts.extend(current_content)
        
        result = '\n'.join(filtered_parts)
        if not result:
            logger.warning("No matching tables found in schema")
            return schema
            
        return result
        
    except Exception as e:
        logger.error(f"Error filtering schema: {str(e)}")
        return schema

def generate_sql_chain():
    """Generate SQL query from natural language"""
    template = """Based on the following schema and question, generate a SQL query.
If tables not mentioned in the schema are referenced, respond with:
"Please select the relevant tables first."

Available Schema:
{schema}

Question: {question}

Write only the SQL query without any additional text."""

    prompt = ChatPromptTemplate.from_template(template)
    
    def get_filtered_schema(vars: dict) -> str:
        selected_tables = st.session_state.get('selected_tables', [])
        return get_schema(selected_tables)
    
    try:
        sql_chain = (
            RunnablePassthrough()
            | {"schema": get_filtered_schema, "question": lambda x: x["question"]}
            | prompt
            | llm
            | StrOutputParser()
        )
        return sql_chain
        
    except Exception as e:
        logger.error(f"Error generating SQL chain: {str(e)}")
        raise

def get_default_insights() -> List[Dict]:
    """
    Obtiene información básica sobre las tablas disponibles
    y genera un resumen inicial
    """
    try:
        selected_tables = st.session_state.get('selected_tables', [])
        if not selected_tables:
            return []

        columns_data = []
        for table in selected_tables:
            try:
                query = f"""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(
                        (
                            SELECT GROUP_CONCAT(COLUMN_NAME)
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_NAME = '{table}'
                            AND TABLE_SCHEMA = DATABASE()
                        ),
                        ''
                    ) as columns
                FROM {table}
                """
                result = run_query(query)
                if result and len(result) > 0:
                    row = result[0]
                    count = row[0] if len(row) > 0 else 0
                    columns = row[1] if len(row) > 1 else ''
                    
                    columns_data.append({
                        "table": table,
                        "count": count,
                        "columns": columns.split(',') if columns else []
                    })
                else:
                    columns_data.append({
                        "table": table,
                        "count": 0,
                        "columns": []
                    })
            except Exception as e:
                logger.error(f"Error getting info for table {table}: {str(e)}")
                columns_data.append({
                    "table": table,
                    "count": 0,
                    "columns": []
                })
        
        return columns_data

    except Exception as e:
        logger.error(f"Error getting default insights: {str(e)}")
        return []

def generate_schema_suggestions(schema_data: List[Dict]) -> str:
    """Genera sugerencias de preguntas basadas en el esquema"""
    template = """Given this database structure:
{schema_data}

Generate 3 basic analytical questions that could be answered with this data. Focus on:
1. Basic counts and distributions
2. Time-based analysis if date fields are available
3. Category or group comparisons if categorical fields exist

Return just the numbered list in Spanish."""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    try:
        suggestions = chain.invoke({"schema_data": str(schema_data)})
        return suggestions
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        return ""

def generate_response_chain(sql_chain):
    """Generate natural language response focused on data analysis"""
    template_response = """You are Quipu AI, a data analyst specialized in exploring and providing insights.
Always maintain a professional, analytical tone and focus on data possibilities.

Context:
- Question: {question}
- Available Schema: {schema}
- SQL Query Used: {query}
- Query Results: {response}
- Selected Tables: {selected_tables}

Response Guidelines:
1. Greetings/General Questions:
   - Briefly acknowledge (1 sentence max)
   - Immediately transition to data overview
   - Share 2-3 specific insights
   - Suggest concrete analytical questions
   
2. Specific Analysis Questions:
   - Provide direct answer with numerical details
   - Add context and patterns
   - Compare with related metrics when possible
   - Suggest follow-up analyses

Important:
- Always be data-centric and analytical
- Minimize casual conversation
- Focus on metrics, patterns, and insights
- ALWAYS respond in the same language as the question
- If sharing numerical results, add them at the end as:
DATA:[("category1",number1),("category2",number2),...]"""

    prompt_response = ChatPromptTemplate.from_template(template_response)

    try:
        full_chain = (
            RunnablePassthrough.assign(query=sql_chain).assign(
                schema=lambda vars: get_schema(st.session_state.get('selected_tables', [])),
                selected_tables=lambda vars: st.session_state.get('selected_tables', []),
                response=lambda vars: run_query(vars["query"])
            )
            | prompt_response
            | llm
            | StrOutputParser()
        )
        return full_chain
    except Exception as e:
        logger.error(f"Error generating response chain: {str(e)}")
        raise

def process_user_query(question: str) -> Dict[str, Any]:
    """
    Procesa la entrada del usuario de manera unificada
    """
    try:
        # Verificar tablas seleccionadas
        selected_tables = st.session_state.get('selected_tables', [])
        if not selected_tables:
            return {
                'question': question,
                'response': "Please select at least one table before querying.",
                'query': None,
                'visualization_data': None
            }

        # Procesar consulta
        sql_chain = generate_sql_chain()
        full_chain = generate_response_chain(sql_chain)
        
        query = sql_chain.invoke({
            "question": question,
            "selected_tables": selected_tables
        })
        
        response = full_chain.invoke({
            "question": question,
            "query": query,
            "selected_tables": selected_tables
        })
        
        # Procesar visualización
        visualization_data = None
        if "DATA:" in response:
            try:
                main_response = response.split("DATA:")[0]
                data_str = response.split("DATA:")[1].strip()
                if data_str:
                    data_list = eval(data_str)
                    if isinstance(data_list, (list, tuple)) and len(data_list) > 0:
                        visualization_data = [
                            {"Categoría": str(cat), "Cantidad": float(count)}
                            for cat, count in data_list
                        ]
                response = main_response
            except Exception as e:
                logger.error(f"Error processing visualization data: {str(e)}")
        
        return {
            'question': question,
            'response': response,
            'query': query,
            'visualization_data': visualization_data
        }
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'question': question,
            'response': f"Error processing query: {str(e)}",
            'query': None,
            'visualization_data': None
        }
    
def format_schema_overview(schema_data: List[Dict]) -> str:
    """Formatea la información del esquema de manera legible"""
    overview = []
    for table in schema_data:
        overview.append(f"""
Tabla: {table['table']}
- Columnas ({len(table['columns'])}): {', '.join(table['columns'])}
- Registros: {table['count']}
""")
    return '\n'.join(overview)