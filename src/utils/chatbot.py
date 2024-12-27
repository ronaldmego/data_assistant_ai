# src/utils/chatbot.py
from typing import Dict, List, Union, Any, Tuple, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
import logging
from .database import get_schema, run_query, get_all_tables
from config.config import OPENAI_API_KEY
import pandas as pd

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

def generate_sql_chain():
    """Generate SQL query from natural language"""
    template = """Based on the provided table schema for the selected tables, analyze if the user's question requires a specific SQL query.
If it's a greeting or general question, return this SQL to get an overview of the selected tables:
"SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name IN ({table_list})"

If it's a specific analytical question, write a SQL query that answers it using only the selected tables.

Selected Tables Schema:
{schema}

Question: {question}

Write only the SQL query without any additional text:"""

    prompt = ChatPromptTemplate.from_template(template)
    
    def format_input(vars: Dict[str, Any]) -> Dict[str, Any]:
        """Format input for the prompt template"""
        selected_tables = vars.get("selected_tables", [])
        schema = get_schema(selected_tables)
        # Format table list for SQL IN clause
        table_list = "'" + "','".join(selected_tables) + "'" if selected_tables else "''"
        return {
            "schema": schema,
            "question": vars["question"],
            "table_list": table_list
        }
    
    try:
        sql_chain = (
            RunnablePassthrough()
            | format_input
            | prompt
            | llm.bind(stop=["\nSQLResult:"])
            | StrOutputParser()
        )
        return sql_chain
    except Exception as e:
        logger.error(f"Error generating SQL chain: {str(e)}")
        raise

def generate_response_chain(sql_chain):
    """Generate natural language response focused on data analysis"""
    template_response = """You are Quipu AI, a data analyst specialized in exploring and providing insights.
Always maintain a professional, analytical tone and focus on data possibilities.

Context:
- Question: {question}
- Selected Tables: {selected_tables}
- Available Schema: {schema}
- SQL Query Used: {query}
- Query Results: {response}
- Schema Insights: {insights}
- Suggested Analyses: {suggestions}

Response Guidelines:
1. Greetings/General Questions:
   - Briefly acknowledge (1 sentence max)
   - Share insights about selected tables
   - Focus on data overview for selected tables
   - Suggest concrete analytical questions for these tables
   
2. Specific Analysis Questions:
   - Provide direct answer with numerical details
   - Add context and patterns
   - Compare with related metrics when possible
   - Suggest follow-up analyses within selected tables

Important:
- Always be data-centric and analytical
- Minimize casual conversation
- Focus on metrics, patterns, and insights
- ALWAYS respond in the same language as the question
- If sharing numerical results, add them at the end as:
DATA:[("category1",number1),("category2",number2),...]"""

    prompt_response = ChatPromptTemplate.from_template(template_response)
    
    def process_response(vars: Dict[str, Any]) -> Dict[str, Any]:
        """Process response before sending to LLM"""
        try:
            # Get schema insights and suggestions
            schema_data = get_default_insights(vars.get("selected_tables", []))
            schema_suggestions = generate_schema_suggestions(schema_data)
            
            # Add to vars
            vars["insights"] = schema_data
            vars["suggestions"] = schema_suggestions
            
            # Process response
            if isinstance(vars["response"], str):
                try:
                    vars["response"] = eval(vars["response"])
                except:
                    pass
            return vars
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return vars

    try:
        full_chain = (
            RunnablePassthrough.assign(query=sql_chain).assign(
                schema=lambda vars: get_schema(vars.get("selected_tables", [])),
                response=lambda vars: run_query(vars["query"])
            )
            | process_response
            | prompt_response
            | llm
            | StrOutputParser()
        )
        return full_chain
    except Exception as e:
        logger.error(f"Error generating response chain: {str(e)}")
        raise

def get_default_insights(selected_tables: List[str]) -> List[Dict]:
    """
    Obtiene información básica sobre las tablas seleccionadas
    y genera un resumen inicial
    """
    try:
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
    """
    Genera sugerencias de preguntas basadas en el esquema
    """
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

def process_user_query(question: str) -> Dict[str, Any]:
    """
    Procesa la entrada del usuario de manera unificada
    """
    try:
        # Obtener información base del esquema
        schema_data = get_default_insights()
        
        # Procesar la consulta
        sql_chain = generate_sql_chain()
        full_chain = generate_response_chain(sql_chain)
        
        query = sql_chain.invoke({"question": question})
        response = full_chain.invoke({
            "question": question,
            "query": query,
            "schema_data": schema_data  # Pasar los insights al chain
        })
        
        # Procesar datos para visualización si están disponibles
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
                response = main_response  # Eliminar la parte DATA: de la respuesta
            except Exception as e:
                logger.error(f"Error processing visualization data: {str(e)}")
        
        return {
            'question': question,
            'response': response,
            'query': query,
            'visualization_data': visualization_data
        }
            
    except Exception as e:
        logger.error(f"Error in process_user_query: {str(e)}")
        return {
            'question': question,
            'response': f"Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
            'query': None,
            'visualization_data': None
        }

def handle_specific_query(question: str) -> Dict[str, Any]:
    """
    Maneja consultas específicas sobre los datos
    """
    sql_chain = generate_sql_chain()
    full_chain = generate_response_chain(sql_chain)
    
    query = sql_chain.invoke({"question": question})
    response = full_chain.invoke({
        "question": question,
        "query": query
    })
    
    # Procesar datos para visualización si están disponibles
    visualization_data = None
    if "DATA:" in response:
        try:
            main_response, data_str = response.split("DATA:")
            data_list = eval(data_str.strip())
            visualization_data = [{"Categoría": cat, "Cantidad": count} for cat, count in data_list]
        except Exception as e:
            logger.error(f"Error processing visualization data: {str(e)}")
    
    return {
        'question': question,
        'response': response,
        'query': query,
        'visualization_data': visualization_data
    }

def handle_schema_overview(schema_data: List[Dict]) -> Dict[str, Any]:
    """
    Genera una visión general de la base de datos
    """
    # Query para obtener una muestra de cada tabla
    overview_data = []
    for table_info in schema_data:
        query = f"SELECT * FROM {table_info['table']} LIMIT 5"
        sample_data = run_query(query)
        overview_data.append({
            'table': table_info['table'],
            'sample': sample_data
        })
    
    # Generar sugerencias basadas en el esquema
    suggestions = generate_schema_suggestions(schema_data)
    
    response = f"""
Aquí está un resumen de los datos disponibles:

{format_schema_overview(schema_data)}

Algunas preguntas que podrías hacer:
{suggestions}
    """
    
    return {
        'question': "Visión general de la base de datos",
        'response': response,
        'query': "SELECT * FROM information_schema.columns WHERE table_schema = DATABASE()",
        'visualization_data': [
            {"Categoría": table["table"], "Cantidad": len(table["columns"])}
            for table in schema_data
        ]
    }

def handle_conversational_response(question: str, schema_data: List[Dict]) -> Dict[str, Any]:
    """
    Maneja respuestas conversacionales incluyendo información útil
    """
    suggestions = generate_schema_suggestions(schema_data)
    
    template = """You are Quipu AI, a data analysis assistant. 
Respond to this conversational input while maintaining focus on data analysis capabilities.

Question: {question}
Available Data Overview: {schema_overview}
Suggested Questions: {suggestions}

Craft a response that:
1. Acknowledges the user's input
2. Maintains a professional but friendly tone
3. Guides the user towards data exploration
4. Includes the suggested questions naturally in the conversation

Response in Spanish:"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "question": question,
        "schema_overview": format_schema_overview(schema_data),
        "suggestions": suggestions
    })
    
    return {
        'question': question,
        'response': response,
        'query': None,
        'visualization_data': None
    }

def format_schema_overview(schema_data: List[Dict]) -> str:
    """
    Formatea la información del esquema de manera legible
    """
    overview = []
    for table in schema_data:
        overview.append(f"""
Tabla: {table['table']}
- Columnas ({len(table['columns'])}): {', '.join(table['columns'])}
- Registros: {table['count']}
""")
    return '\n'.join(overview)