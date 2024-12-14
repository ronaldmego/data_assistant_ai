from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from database import get_schema, run_query
from config import OPENAI_API_KEY

# Inicializar el modelo de lenguaje
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o-mini")

def generate_sql_chain():
    template = """Based on the provided table schema, write a SQL query that answers the user's question. Respond with only the SQL query in plain text. Do not include any additional text or symbols:
{schema}
Question: {question}
SQL Query:"""
    prompt = ChatPromptTemplate.from_template(template)
    sql_chain = (
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm.bind(stop=["\nSQLResult:"])
        | StrOutputParser()
    )
    return sql_chain

def generate_response_chain(sql_chain):
    template_response = """Here is the result of your query:
Question: {question}
SQL Query: {query}
SQL Response: {response}

Instructions for formatting the answer:
1. If the response contains only one total/count, respond in a simple sentence.
2. If the response contains multiple categories with their respective counts, format your response as follows:
   First provide a brief summary sentence.
   Then list the data in this format:
   DATA_START
   Category: [category_name], Count: [number]
   Category: [category_name], Count: [number]
   ...
   DATA_END

Example single value response:
"The total number of records in the database is 1,234."

Example multiple values response:
"Here's the distribution of incidents by type:"
DATA_START
Category: Theft, Count: 1234
Category: Fraud, Count: 567
Category: Vandalism, Count: 890
DATA_END

Please provide your response following these formatting rules:"""

    prompt_response = ChatPromptTemplate.from_template(template_response)
    
    full_chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
            schema=get_schema,
            response=lambda vars: run_query(vars["query"]),
        )
        | prompt_response
        | llm
        | StrOutputParser()
    )
    return full_chain