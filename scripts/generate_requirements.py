from importlib.metadata import version, PackageNotFoundError
from typing import Dict, List

def get_package_version(package_name: str) -> str:
    """Get package version, handling package name variations"""
    try:
        # Limpiar el nombre del paquete para la búsqueda de versión
        lookup_name = package_name.split('[')[0]  # Remover extras como [ollama]
        return version(lookup_name)
    except PackageNotFoundError:
        return None

def generate_requirements() -> None:
    """Generate requirements.txt with organized dependencies"""
    
    # Organizar paquetes por categorías
    packages: Dict[str, List[str]] = {
        "Core Dependencies": [
            "streamlit",
            "langchain",
            "langchain-core",
            "langchain-openai",
            "langchain-community",
            "langchain-ollama",
        ],
        "Database": [
            "mysql-connector-python",
            "python-dotenv",
        ],
        "Data Processing": [
            "pandas",
            "numpy",
        ],
        "Visualization": [
            "matplotlib",
            "seaborn",
        ],
        "Machine Learning": [
            "faiss-cpu",
        ],
        "Document Processing": [
            "pypdf",
        ],
        "Utilities": [
            "requests",
        ],
    }

    try:
        with open('requirements.txt', 'w') as f:
            for category, pkg_list in packages.items():
                # Añadir comentario de categoría
                f.write(f"# {category}\n")
                
                for package in pkg_list:
                    version_str = get_package_version(package)
                    if version_str:
                        # Extraer versión major.minor.patch
                        version_parts = version_str.split('.')
                        if len(version_parts) >= 3:
                            major_minor_patch = '.'.join(version_parts[:3])
                            f.write(f"{package}>={major_minor_patch}\n")
                        else:
                            f.write(f"{package}>={version_str}\n")
                    else:
                        print(f"Warning: Version not found for {package}")
                        f.write(f"{package}\n")
                
                # Añadir línea en blanco entre categorías
                f.write("\n")
                
        print("✅ requirements.txt generated successfully!")
        
    except Exception as e:
        print(f"❌ Error generating requirements.txt: {str(e)}")

if __name__ == "__main__":
    generate_requirements()