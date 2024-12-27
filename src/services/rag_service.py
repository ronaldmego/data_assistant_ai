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
from ..utils.schema_utils import chunk_schema

logger = logging.getLogger(__name__)

MAX_TOKENS = 4000  # Establecer un límite seguro de tokens

def initialize_rag_components():
    """Initialize RAG components in session state"""
    if 'rag_initialized' not in st.session_state:
        try:
            # Initialize embeddings
            api_key = st.session_state.get('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OpenAI API key not found in session state")
                st.session_state['rag_initialized'] = False
                st.error("OpenAI API key not found.")
                return

            with st.spinner("Initializing AI components..."):
                embeddings = initialize_embeddings(api_key)
                
                # Load documents
                cwd = Path.cwd()
                logger.info(f"Current working directory: {cwd}")
                
                docs_path = Path("docs")
                if not docs_path.exists():
                    docs_path = cwd / "docs"
                    logger.info(f"Trying absolute path: {docs_path}")
                
                logger.info(f"Looking for documents in: {docs_path}")
                documents = load_documents(docs_path)
                
                if not documents:
                    logger.warning("No documents found, RAG will be disabled")
                    st.session_state['rag_initialized'] = False
                    st.warning("No documents found for enhanced responses.")
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
                st.success("AI components initialized successfully!")
                    
        except Exception as e:
            logger.error(f"Error initializing RAG components: {e}")
            st.session_state['rag_initialized'] = False
            st.error(f"Error initializing AI components: {str(e)}")

def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text using a simple approximation"""
    # Aproximación simple: 1 token ≈ 4 caracteres en promedio
    return len(text) // 4

def process_query_with_rag(question: str) -> Dict:
    """Process query using RAG enhancement"""
    try:
        if not st.session_state.get('rag_initialized'):
            return {'question': question, 'error': 'RAG not initialized'}
            
        # Get vector store and memory
        vector_store = st.session_state.get('vector_store')
        memory = st.session_state.get('conversation_memory')
        
        # Get context from documents (limitar a 2 para reducir tokens)
        context = []
        if vector_store:
            context = vector_store.similarity_search(question, k=2)
        
        # Get schema for selected tables only
        selected_tables = st.session_state.get('selected_tables', [])
        if not selected_tables:
            return {
                'question': question,
                'error': 'No tables selected',
                'query': "SELECT 1"
            }
        
        # Get filtered schema based on selected tables
        schema = get_schema(selected_tables)
        
        # Estimate tokens
        estimated_tokens = estimate_tokens(schema)
        if estimated_tokens > MAX_TOKENS:
            logger.warning(f"Schema too large ({estimated_tokens} tokens), chunking...")
            schema_chunks = chunk_schema(schema, max_chunks=3)
            schema_preview = schema_chunks[0] if schema_chunks else ""
        else:
            schema_preview = schema
            
        if not schema_preview:
            logger.error("No schema available")
            return {
                'question': question,
                'error': 'No schema available',
                'query': "SELECT 1"
            }
        
        # Preparar contexto reducido de documentos
        doc_context = []
        for doc in context:
            content = doc.page_content[:500]  # Limitar a 500 caracteres por documento
            doc_context.append(content)
        
        # Create enhanced prompt with reduced context
        enhanced_prompt = f"""
        Based on:
        - Available Schema Preview: {schema_preview}
        - Document Context Preview: {doc_context[:1000] if doc_context else 'No additional context'}
        - Question: {question}
        
        Generate an appropriate SQL query that answers the question.
        Focus on the selected tables: {', '.join(selected_tables)}
        """
        
        # Generate query
        sql_chain = generate_sql_chain()
        query = sql_chain.invoke({"question": enhanced_prompt})
        
        # Update memory
        if memory:
            memory.save_context(
                {"question": question},
                {"answer": str(query)}
            )
        
        return {
            'question': question,
            'query': query,
            'context_used': doc_context[:1],  # Solo usar el primer documento de contexto
            'chat_history': memory.load_memory_variables({}).get('chat_history', '') if memory else ''
        }
        
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}")
        return {
            'question': question,
            'error': str(e),
            'query': "SELECT 1"
        }