import PyInstaller.__main__
import streamlit.web.cli as stcli
import os, sys
import webbrowser
from threading import Thread

def resource_path(relative_path):
    """ Hilfsfunktion um Pfade innerhalb der App-Paketierung zu finden """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_streamlit():
    # Pfad zur app.py innerhalb des Pakets
    app_path = resource_path("app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    stcli.main()

if __name__ == "__main__":
    # Startet Streamlit in einem eigenen Thread
    thread = Thread(target=run_streamlit)
    thread.start()
    
    # Öffnet nach einer kurzen Verzögerung den Browser
    import time
    time.sleep(2) 
    webbrowser.open("http://localhost:8501")