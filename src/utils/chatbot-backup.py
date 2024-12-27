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
from typing import TYPE_CHECKING
from src.utils.schema_utils import analyze_table_name_pattern, get_relevant_tables, chunk_schema

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

# utils/chatbot.py

def generate_sql_chain():
    """Generate SQL query from natural language"""
    template = """Based on the following schema chunk and question, analyze if a SQL query is needed.
If it's a greeting or general question, return this SQL:
"SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = DATABASE()"

Schema Chunk {chunk_number} of {total_chunks}:
{schema_chunk}

Question: {question}

Additional Context: This is chunk {chunk_number} of {total_chunks}. Only write a SQL query if you're confident this chunk contains the relevant tables.
If you need to see other chunks, return: "NEED_MORE_CHUNKS"

Write only the SQL query without any additional text:"""

    prompt = ChatPromptTemplate.from_template(template)
    
    try:
        def process_with_chunks(inputs: dict) -> str:
            # Obtener schema completo
            full_schema = get_schema()
            
            # Analizar patrones en nombres de tablas
            table_names = get_all_tables()
            patterns = analyze_table_name_pattern(table_names)
            
            # Obtener tablas relevantes
            relevant_tables = get_relevant_tables(patterns, inputs['question'])
            
            # Obtener solo el esquema de las tablas relevantes
            relevant_schema = filter_schema_for_tables(full_schema, relevant_tables)
            
            # Dividir en chunks si es necesario
            schema_chunks = chunk_schema(relevant_schema)
            
            for i, chunk in enumerate(schema_chunks, 1):
                # Procesar cada chunk
                response = prompt.format(
                    schema_chunk=chunk,
                    question=inputs['question'],
                    chunk_number=i,
                    total_chunks=len(schema_chunks)
                )
                
                result = llm.invoke(response)
                
                # Extraer el contenido del mensaje
                if hasattr(result, 'content'):
                    result_text = result.content
                else:
                    result_text = str(result)
                
                if result_text and "NEED_MORE_CHUNKS" not in result_text:
                    return result_text
            
            # Si llegamos aquí, usar el último resultado
            return result_text if 'result_text' in locals() else "SELECT 1"
        
        sql_chain = (
            RunnablePassthrough()
            | process_with_chunks
            | StrOutputParser()
        )
        return sql_chain
        
    except Exception as e:
        logger.error(f"Error generating SQL chain: {str(e)}")
        raise

def filter_schema_for_tables(schema: str, table_names: List[str]) -> str:
    """
    Filtra el esquema para incluir solo las tablas especificadas
    """
    if not schema or not table_names:
        logger.warning("Empty schema or table names provided")
        return ""
        
    try:
        filtered_parts = []
        current_table = ""
        current_content = []
        
        for line in schema.split('\n'):
            if line.startswith('CREATE TABLE'):
                # Procesar tabla anterior si existe
                if current_table and current_table in table_names:
                    filtered_parts.extend(current_content)
                # Iniciar nueva tabla
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
            elif current_table:  # Solo agregar líneas si estamos dentro de una tabla
                current_content.append(line)
        
        # Procesar última tabla si existe
        if current_table and current_table in table_names:
            filtered_parts.extend(current_content)
        
        result = '\n'.join(filtered_parts)
        if not result:
            logger.warning("No matching tables found in schema")
            return schema  # Devolver esquema completo si no se encontraron coincidencias
            
        return result
        
    except Exception as e:
        logger.error(f"Error filtering schema: {str(e)}")
        return schema  # Devolver esquema completo en caso de error

def generate_response_chain(sql_chain):
    """Generate natural language response focused on data analysis"""
    template_response = """You are Quipu AI, a data analyst specialized in exploring and providing insights.
Always maintain a professional, analytical tone and focus on data possibilities.

Context:
- Question: {question}
- Available Schema: {schema}
- SQL Query Used: {query}
- Query Results: {response}
- Schema Insights: {insights}
- Suggested Analyses: {suggestions}

Response Guidelines:
1. Greetings/General Questions:
   - Briefly acknowledge (1 sentence max)
   - Immediately transition to data overview
   - Share 2-3 specific insights from the schema
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
    
    def process_response(vars: Dict[str, Any]) -> Dict[str, Any]:
        """Process response before sending to LLM"""
        try:
            # Get schema insights and suggestions
            schema_data = get_default_insights()
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
                schema=get_schema,
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

def get_default_insights() -> List[Dict]:
    """
    Obtiene información básica sobre las tablas disponibles
    y genera un resumen inicial
    """
    try:
        schema = get_schema()
        tables = get_all_tables()
        
        # Query para contar columnas por tabla
        columns_data = []
        for table in tables:
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
                    # Asegurarse de que tenemos ambos valores
                    row = result[0]
                    count = row[0] if len(row) > 0 else 0
                    columns = row[1] if len(row) > 1 else ''
                    
                    columns_data.append({
                        "table": table,
                        "count": count,
                        "columns": columns.split(',') if columns else []
                    })
                else:
                    # Añadir entrada con valores por defecto si no hay resultados
                    columns_data.append({
                        "table": table,
                        "count": 0,
                        "columns": []
                    })
            except Exception as e:
                logger.error(f"Error getting info for table {table}: {str(e)}")
                # Añadir entrada con valores por defecto en caso de error
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