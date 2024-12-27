# src/utils/schema_utils.py
import streamlit as st
import re
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def analyze_table_name_pattern(table_names: List[str]) -> Dict:
    """
    Analiza los nombres de las tablas para detectar patrones temporales
    """
    try:
        patterns = {}
        for table in table_names:
            # Buscar patrón YYYYMM al final del nombre
            match = re.search(r'(\d{6})$', table)
            if match:
                base_name = table[:match.start()]
                if base_name not in patterns:
                    patterns[base_name] = {
                        'type': 'temporal',
                        'tables': []
                    }
                patterns[base_name]['tables'].append(table)
            else:
                patterns[table] = {
                    'type': 'static',
                    'tables': [table]
                }
        
        logger.info(f"Analyzed patterns in {len(table_names)} tables")
        return patterns
        
    except Exception as e:
        logger.error(f"Error analyzing table patterns: {str(e)}")
        return {}

def get_relevant_tables(patterns: Dict, question: str) -> List[str]:
    """
    Selecciona las tablas relevantes basado en la pregunta y los patrones
    """
    try:
        relevant_tables = []
        
        # Si no hay patrones, devolver lista vacía
        if not patterns:
            logger.warning("No patterns provided for table analysis")
            return []
        
        for base_name, info in patterns.items():
            if info['type'] == 'temporal':
                # Buscar fechas específicas en la pregunta
                date_matches = re.findall(r'(\d{4})[-/]?(\d{2})', question)
                
                if date_matches:
                    # Si hay fechas específicas, usar esas fechas
                    for year, month in date_matches:
                        pattern = f"{base_name}{year}{month}"
                        matching_tables = [t for t in info['tables'] if pattern in t]
                        relevant_tables.extend(matching_tables)
                else:
                    # Si no hay fechas específicas, usar las últimas 3 tablas
                    sorted_tables = sorted(info['tables'])
                    if sorted_tables:  # Verificar que hay tablas
                        relevant_tables.extend(sorted_tables[-3:])
            else:
                # Para tablas no temporales, incluirlas siempre
                relevant_tables.extend(info['tables'])
        
        # Si no se encontraron tablas relevantes, usar las últimas 3 tablas
        if not relevant_tables and patterns:
            all_tables = []
            for info in patterns.values():
                all_tables.extend(info['tables'])
            sorted_tables = sorted(all_tables)
            if sorted_tables:  # Verificar que hay tablas
                relevant_tables.extend(sorted_tables[-3:])
        
        logger.info(f"Selected {len(relevant_tables)} relevant tables")
        return list(set(relevant_tables))  # Eliminar duplicados
        
    except Exception as e:
        logger.error(f"Error getting relevant tables: {str(e)}")
        return []

def chunk_schema(schema: str, max_chunks: int = 3) -> List[str]:
    """
    Divide el esquema en chunks más pequeños
    """
    try:
        if not schema:
            logger.warning("Empty schema provided for chunking")
            return []
            
        table_chunks = schema.split('CREATE TABLE')
        clean_chunks = [chunk for chunk in table_chunks if chunk.strip()]
        
        if len(clean_chunks) <= max_chunks:
            return [schema]
        
        # Calcular tamaño aproximado por chunk
        chunk_size = len(clean_chunks) // max_chunks
        if chunk_size < 1:
            chunk_size = 1
        
        # Dividir en chunks
        result_chunks = []
        current_chunk = []
        current_size = 0
        
        for table in clean_chunks:
            if current_size >= chunk_size and current_chunk:
                result_chunks.append('CREATE TABLE' + ''.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(table)
            current_size += 1
        
        # Añadir el último chunk si queda algo
        if current_chunk:
            result_chunks.append('CREATE TABLE' + ''.join(current_chunk))
        
        logger.info(f"Split schema into {len(result_chunks)} chunks")
        return result_chunks
        
    except Exception as e:
        logger.error(f"Error chunking schema: {str(e)}")
        return [schema] if schema else []