import os
import subprocess
import sys
from pathlib import Path

def install_requirements():
    """install pckg"""
    print("inst req...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_executable():
    """Build with PyInstaller"""
    print("Building")
    
    Path("downloads").mkdir(exist_ok=True)
    
    cmd = [
        "pyinstaller",
        "--name=YTDownloader",
        "--onefile", 
        "--windowed", 
        "--add-data=Tool:Tool",  
        "--icon=Tool/icon.ico" if os.path.exists("Tool/icon.ico") else "", 
        "Tool/main.py"
    ]
    
    cmd = [x for x in cmd if x]
    
    try:
        subprocess.check_call(cmd)
        print("\nSuccess!")
        print(f"Executable location: {os.path.abspath('dist/YTDownloader')}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

def main():
    """Main"""
    print("Starting...")
    install_requirements()
    build_executable()

if __name__ == "__main__":
    main()