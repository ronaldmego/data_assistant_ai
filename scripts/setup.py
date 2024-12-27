import os
import subprocess
import sys
import platform

def create_venv():
    """Create virtual environment"""
    print("Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])

def get_activate_command():
    """Get the appropriate activate command based on OS"""
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "activate")
    return "source venv/bin/activate"

def install_requirements():
    """Install required packages"""
    pip_cmd = os.path.join("venv", "Scripts", "pip") if platform.system() == "Windows" else "venv/bin/pip"
    
    print("Installing required packages...")
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
        "pypdf"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        subprocess.check_call([pip_cmd, "install", package])
    
    # Generate requirements.txt
    print("Generating requirements.txt...")
    subprocess.check_call([pip_cmd, "freeze", ">", "requirements.txt"], shell=True)

def main():
    try:
        create_venv()
        activate_cmd = get_activate_command()
        print(f"\nVirtual environment created successfully!")
        print("\nTo activate the virtual environment:")
        print(f"Run: {activate_cmd}")
        print("\nInstalling dependencies...")
        install_requirements()
        print("\nSetup completed successfully!")
        print("\nDon't forget to create a .env file with your configuration:")
        print("""
        OPENAI_API_KEY=your_key_here
        MYSQL_USER=your_user
        MYSQL_PASSWORD=your_password
        MYSQL_HOST=your_host
        MYSQL_DATABASE=your_database
        IGNORED_TABLES=table1,table2,table3
        """)
        
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()