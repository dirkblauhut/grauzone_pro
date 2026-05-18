import os
import subprocess
import sys

def setup():
    print("--- Grauzone Setup startet ---")
    
    # 1. Bibliotheken installieren
    print("Installiere Abhängigkeiten...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 2. KI-Modelle laden
    print("Lade spaCy Sprachmodell (lg)...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "de_core_news_lg"])
    
    # 3. Grundstruktur prüfen
    if not os.path.exists("vornamen.txt"):
        with open("vornamen.txt", "w") as f:
            f.write("Anni\nDirk\n")
        print("vornamen.txt wurde erstellt.")

    print("\n✅ Setup abgeschlossen! Starte die App mit: streamlit run app.py")

if __name__ == "__main__":
    setup()