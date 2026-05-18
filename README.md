# 🛡️ Grauzone PRO: Lokale PDF-Anonymisierung

Grauzone PRO ist eine leistungsstarke, datenschutzkonforme Desktop-Anwendung zur automatischen Erkennung und Schwärzung von personenbezogenen Daten (PII) in PDF-Dokumenten. 

**Der entscheidende Vorteil:** Alle Prozesse laufen zu 100 % lokal auf deinem Rechner ab. Es werden keine Daten in eine Cloud hochgeladen – ideal für sensible Dokumente, Anwaltskanzleien oder Behörden.

---

## ✨ Hauptfunktionen

- **KI-gestützte Erkennung:** Nutzt moderne NLP-Modelle (spaCy) zur Identifikation von Namen, Orten und Organisationen.
- **Integrierte OCR:** Dank EasyOCR wird Text auch in gescannten PDFs oder Bildern zuverlässig erkannt.
- **Kontext-Intelligenz:** Automatische Erkennung von Telefonnummern und Namen durch Kontext-Keywords (z.B. "Herr", "Frau", "Tel:").
- **Lernfähiges System:** Eine integrierte Knowledge Base merkt sich deine manuellen Korrekturen (Whitelist/Blacklist).
- **Interaktive Vorschau:** Markiere Begriffe direkt in der Benutzeroberfläche und exportiere das fertige, geschwärzte PDF mit einem Klick.
- **Wissens-Monitor:** Verfolge in der Seitenleiste live den Lernfortschritt der KI.

---

## 🛠️ Installation (Entwickler-Modus)

Um die Anwendung aus dem Quellcode zu starten, folge diesen Schritten:

### 1. Repository klonen
```bash
git clone [https://github.com/DEIN_USERNAME/grauzone.git](https://github.com/DEIN_USERNAME/grauzone.git)
cd grauzone

### 2. Virtuelle Umgebung erstellen & aktivieren
Auf dem Mac:

Bash
python -m venv venv
source venv/bin/activate
Auf Windows:

Bash
python -m venv venv
venv\Scripts\activate

### 3. Setup ausführen
Dieses Skript installiert alle benötigten Bibliotheken und lädt die notwendigen KI-Sprachmodelle (spaCy de_core_news_lg) herunter:

Bash
python setup_project.py

### 4. App starten
Bash
streamlit run app.py

### 📦 Paketierung als Desktop-App (.app / .exe)
Du kannst das Tool als eigenständige Datei für Kollegen bereitstellen, die kein Python installiert haben. Wir nutzen dafür PyInstaller.

Führe diesen Befehl im aktivierten venv aus:

Bash
python -m PyInstaller --noconfirm --onefile --windowed \
--additional-hooks-dir=./hooks \
--collect-all easyocr \
--collect-all spacy \
--collect-all de_core_news_lg \
--add-data "app.py:." \
--add-data "vornamen.txt:." \
--add-data "knowledge_base.json:." \
run_app.py
Die fertige App findest du anschließend im Ordner dist/.

### 📂 Projektstruktur
app.py: Die Hauptanwendung (Streamlit Interface).

run_app.py: Der Wrapper-Starter für die Desktop-App.

setup_project.py: Automatisiertes Installations-Skript.

knowledge_base.json: Speichert gelernte Begriffe (lokale Datenbank).

vornamen.txt: Abgleich-Datenbank für die Namenserkennung.

hooks/: Notwendige Konfigurationen für den PyInstaller-Build.

### 🔒 Datenschutzhinweis
Diese Software wurde mit dem "Privacy by Design"-Prinzip entwickelt.

Keine API-Anbindung: Es werden keine externen Dienste wie OpenAI oder Google Vision verwendet.

Lokale Verarbeitung: Die Texterkennung (OCR) und Analyse findet ausschließlich auf der CPU/GPU des lokalen Rechners statt.

Keine Telemetrie: Es werden keine Nutzungsstatistiken erhoben.

⚖️ Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe LICENSE für Details.


***
