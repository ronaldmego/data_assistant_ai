# utils/logging_config.py
import logging
import sys
from pathlib import Path

def setup_logging():
    """Configure logging for the application"""
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configurar formato
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configurar logging general
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # Log a archivo
            logging.FileHandler(log_dir / "app.log"),
            # Log a consola
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar loggers específicos
    loggers = [
        'chatbot',
        'database',
        'query_interface',
        'visualization',
        'data_processing',
        'rag_service'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # Añadir handler específico para cada componente
        file_handler = logging.FileHandler(log_dir / f"{logger_name}.log")
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)