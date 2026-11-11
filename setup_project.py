import os
import subprocess
import sys

# "python -m spacy download" findet unter spaCy 3.5 keine passende Version
# mehr, daher werden die Modelle direkt über ihre feste Adresse installiert.
MODELLE = ["de_core_news_sm", "de_core_news_lg"]
MODELL_URL = (
    "https://github.com/explosion/spacy-models/releases/download/"
    "{m}-3.5.0/{m}-3.5.0-py3-none-any.whl"
)


def setup():
    print("--- Grauzone Setup startet ---")

    if sys.version_info[:2] > (3, 11):
        sys.exit("Fehler: spaCy 3.5 braucht Python 3.9 bis 3.11 "
                 f"(gefunden: {sys.version.split()[0]}).")

    # 1. Bibliotheken installieren
    print("Installiere Abhängigkeiten...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 2. KI-Modelle laden
    for m in MODELLE:
        print(f"Lade spaCy-Sprachmodell {m}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", MODELL_URL.format(m=m)])

    # 3. Grundstruktur prüfen
    if not os.path.exists("vornamen.txt"):
        with open("vornamen.txt", "w", encoding="utf-8") as f:
            f.write("Anni\nDirk\n")
        print("vornamen.txt wurde erstellt.")

    print("\n✅ Setup abgeschlossen! Starte die App mit: python -m streamlit run app.py")


if __name__ == "__main__":
    setup()
