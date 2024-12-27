# src/services/rag_service.py
import streamlit as st
from pathlib import Path
from typing import Dict, List, Optional
import logging
from ..utils.rag_utils import initialize_embeddings, load_documents, create_vector_store
from ..utils.database import get_all_tables, get_schema
from ..utils.chatbot import generate_sql_chain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from ..utils.schema_utils import analyze_table_name_pattern, get_relevant_tables, chunk_schema

logger = logging.getLogger(__name__)

def initialize_rag_components():
    """Initialize RAG components in session state"""
    if 'rag_initialized' not in st.session_state:
        try:
            # Initialize embeddings
            api_key = st.session_state.get('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OpenAI API key not found in session state")
                st.session_state['rag_initialized'] = False
                return
                
            embeddings = initialize_embeddings(api_key)
            
            # Load documents
            try:
                # Get current working directory for reference
                cwd = Path.cwd()
                logger.info(f"Current working directory: {cwd}")
                
                # Try both relative and absolute paths
                docs_path = Path("docs")
                if not docs_path.exists():
                    # Try looking in the project root
                    docs_path = cwd / "docs"
                    logger.info(f"Trying absolute path: {docs_path}")
                
                logger.info(f"Looking for documents in: {docs_path}")
                documents = load_documents(docs_path)
                
                if not documents:
                    logger.warning("No documents found, RAG will be disabled")
                    st.session_state['rag_initialized'] = False
                    return
                    
            except Exception as e:
                logger.error(f"Error loading documents: {e}")
                st.session_state['rag_initialized'] = False
                return
                
            # Create vector store
            vector_store = create_vector_store(documents, embeddings)
            if not vector_store:
                logger.warning("Failed to create vector store")
                st.session_state['rag_initialized'] = False
                return
                
            # Initialize conversation memory
            msgs = StreamlitChatMessageHistory(key="langchain_messages")
            memory = ConversationBufferMemory(
                chat_memory=msgs,
                memory_key="chat_history",
                return_messages=True
            )
            
            # Store in session state
            st.session_state['vector_store'] = vector_store
            st.session_state['conversation_memory'] = memory
            st.session_state['rag_initialized'] = True
            st.session_state['docs_loaded'] = [str(doc.metadata.get('source', 'Unknown')) for doc in documents]
            
            logger.info("RAG components initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing RAG components: {e}")
            st.session_state['rag_initialized'] = False

def process_query_with_rag(question: str) -> Dict:
    """Process query using RAG enhancement"""
    try:
        if not st.session_state.get('rag_initialized'):
            return {'question': question, 'error': 'RAG not initialized'}
            
        # Get vector store and memory
        vector_store = st.session_state.get('vector_store')
        memory = st.session_state.get('conversation_memory')
        
        # Get context from documents (limitar a 3)
        context = []
        if vector_store:
            context = vector_store.similarity_search(question, k=3)
            
        # Get schema and relevant tables
        table_names = get_all_tables()
        patterns = analyze_table_name_pattern(table_names)
        relevant_tables = get_relevant_tables(patterns, question)
        
        if not relevant_tables:
            logger.warning("No relevant tables found, using default schema")
            schema = get_schema()
            schema_chunks = [schema] if schema else []
        else:
            # Get filtered schema and chunk it
            schema = get_schema()  # You might want to filter this based on relevant_tables
            schema_chunks = chunk_schema(schema) if schema else []
        
        if not schema_chunks:
            logger.error("No schema chunks available")
            return {
                'question': question,
                'error': 'No schema available',
                'query': "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();"
            }
        
        # Preparar contexto reducido del esquema
        schema_preview = schema_chunks[0][:2000] if schema_chunks else "No schema available"
        
        # Preparar contexto reducido de documentos
        doc_context = []
        for doc in context:
            # Tomar solo los primeros 500 caracteres de cada documento
            content = doc.page_content
            preview = content[:500]
            if len(content) > 500:
                preview += "..."
            doc_context.append(preview)
        
        # Create enhanced prompt with reduced context
        enhanced_prompt = f"""
        Based on:
        - Available Schema Preview: {schema_preview}
        - Document Context Preview: {doc_context}
        - Question: {question}
        
        Generate an appropriate SQL query that answers the question.
        If you need more detailed schema information, focus on the most recent or relevant tables.
        The schema may be truncated, so prefer simple queries that don't require full schema details.
        """
        
        # Generate and execute query
        sql_chain = generate_sql_chain()
        query = sql_chain.invoke({"question": enhanced_prompt})
        
        # Update memory if available
        if memory:
            memory.save_context(
                {"question": question},
                {"answer": str(query)}
            )
        
        return {
            'question': question,
            'query': query,
            'context_used': doc_context,  # Usar la versión truncada
            'chat_history': memory.load_memory_variables({}).get('chat_history', '') if memory else ''
        }
        
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}")
        return {
            'question': question,
            'error': str(e),
            'query': "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();"
        }