# src/utils/rag_utils.py
import streamlit as st
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def initialize_embeddings(api_key: str):
    """Initialize OpenAI embeddings"""
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        logger.info("OpenAI embeddings initialized successfully")
        return embeddings
    except Exception as e:
        logger.error(f"Error initializing embeddings: {e}")
        st.error("Failed to initialize AI components. Please check your API key.")
        raise

def load_documents(docs_path: Path) -> List:
    """Load documents from various sources"""
    documents = []
    
    abs_path = docs_path.absolute()
    logger.info(f"Checking for documents in: {abs_path}")
    
    if not docs_path.exists():
        logger.warning(f"Documents directory {abs_path} does not exist")
        docs_path.mkdir(parents=True, exist_ok=True)
        return documents
        
    files = list(docs_path.glob('**/*'))
    logger.info(f"Files found in docs directory: {[str(f) for f in files]}")

    loaders = {
        'pdf': (DirectoryLoader(str(docs_path), glob="**/*.pdf", loader_cls=PyPDFLoader), "PDF documents"),
        'txt': (DirectoryLoader(str(docs_path), glob="**/*.txt", loader_cls=TextLoader), "text documents"),
        'md': (DirectoryLoader(str(docs_path), glob="**/*.md", loader_cls=TextLoader), "markdown documents")
    }
    
    for loader_type, (loader, desc) in loaders.items():
        try:
            loaded_docs = loader.load()
            logger.info(f"Loaded {len(loaded_docs)} {desc}")
            documents.extend(loaded_docs)
        except Exception as e:
            logger.error(f"Error loading {desc}: {e}")
            
    if not documents:
        logger.warning("No documents were successfully loaded")
        st.warning("No documents found in the docs directory.")
    else:
        logger.info(f"Successfully loaded total of {len(documents)} documents")
        for doc in documents:
            logger.info(f"Loaded: {doc.metadata.get('source', 'Unknown source')}")
            
    return documents

def create_vector_store(documents: List, embeddings) -> Optional[FAISS]:
    """Create FAISS vector store from documents"""
    try:
        if not documents:
            logger.warning("No documents provided for vector store creation")
            st.warning("No documents available for processing.")
            return None
            
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False
        )
        chunks = text_splitter.split_documents(documents)
        
        if not chunks:
            logger.warning("No chunks created from documents")
            st.warning("Could not process documents into searchable chunks.")
            return None
            
        vector_store = FAISS.from_documents(chunks, embeddings)
        logger.info("Vector store created successfully")
        return vector_store
        
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        st.error("Failed to create document search index.")
        return None