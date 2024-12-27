from importlib.metadata import version, PackageNotFoundError

def get_package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None

# Lista de paquetes que realmente necesitas
packages = [
    "streamlit",
    "langchain",
    "langchain-openai",
    "langchain-community",
    "mysql-connector-python",
    "python-dotenv",
    "pandas",
    "matplotlib",
    "seaborn",
    "faiss-cpu",
    "pypdf",
    "requests",
    "langchain-community[ollama]"
]

# Generar requirements.txt
with open('requirements.txt', 'w') as f:
    for package in packages:
        try:
            version_str = get_package_version(package)
            if version_str:
                # Extraer solo la versión mayor.minor para hacerlo más flexible
                major_minor = '.'.join(version_str.split('.')[:2])
                f.write(f"{package}>={major_minor}.0\n")
            else:
                print(f"Warning: Version not found for {package}")
                f.write(f"{package}\n")
        except Exception as e:
            print(f"Warning: Could not get version for {package}: {e}")
            f.write(f"{package}\n")

print("requirements.txt generated successfully!")