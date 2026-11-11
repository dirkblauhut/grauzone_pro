#!/bin/bash
# Grauzone PRO – Einrichtung per Doppelklick (macOS)
#
# Richtet alles ein, was Grauzone braucht, und startet danach die App:
#   1. holt das Hilfsprogramm "uv" (falls nicht vorhanden)
#   2. legt mit Python 3.11 eine eigene Umgebung im Ordner "venv" an
#      (uv lädt Python 3.11 bei Bedarf selbst herunter)
#   3. installiert die Bibliotheken aus requirements.txt
#   4. lädt die deutschen spaCy-Sprachmodelle und die EasyOCR-Modelle
#   5. startet Grauzone im Browser
#
# Erneut ausführen ist unschädlich: Vorhandenes wird nur ergänzt.

set -e
cd -- "$(dirname "$0")"

fehler() {
    echo ""
    echo "❌ Einrichtung abgebrochen: $1"
    echo "   Fenster kann geschlossen werden."
    read -r -p "   [Enter] drücken …" _
    exit 1
}
trap 'fehler "unerwarteter Fehler in Zeile $LINENO (siehe Meldungen oben)."' ERR

echo "=== Grauzone PRO – Einrichtung ==="
echo "Ordner: $(pwd)"
echo "Das dauert beim ersten Mal 5–15 Minuten (ca. 2 GB Download)."
echo ""

# --- 1. uv finden oder installieren ---------------------------------------
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "▶ Installiere Hilfsprogramm uv (astral.sh) …"
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh \
        || fehler "uv konnte nicht geladen werden. Besteht eine Internetverbindung?"
fi
command -v uv >/dev/null 2>&1 || fehler "uv wurde nicht gefunden."
echo "✔ uv: $(uv --version)"

# --- 2. Python-3.11-Umgebung ----------------------------------------------
if [ -x venv/bin/python ] && venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
    echo "✔ Umgebung venv (Python 3.11) ist schon vorhanden."
else
    if [ -d venv ]; then
        echo "▶ Vorhandene Umgebung venv hat nicht Python 3.11 – wird neu angelegt …"
        rm -rf venv
    fi
    echo "▶ Lege Umgebung mit Python 3.11 an …"
    uv venv --seed --python 3.11 venv
fi
PY="$(pwd)/venv/bin/python"

# --- 3. Bibliotheken -------------------------------------------------------
echo "▶ Installiere Bibliotheken (u. a. PyTorch, spaCy, Streamlit) …"
uv pip install --python "$PY" -r requirements.txt

# --- 4. Modelle ------------------------------------------------------------
for modell in de_core_news_sm de_core_news_lg; do
    if "$PY" -c "import spacy.util, sys; sys.exit(0 if spacy.util.is_package('$modell') else 1)"; then
        echo "✔ Sprachmodell $modell ist schon da."
    else
        echo "▶ Lade Sprachmodell $modell …"
        # "spacy download" findet unter spaCy 3.5 keine Version mehr -> feste Adresse
        uv pip install --python "$PY" \
            "https://github.com/explosion/spacy-models/releases/download/$modell-3.5.0/$modell-3.5.0-py3-none-any.whl" \
            || echo "⚠ $modell konnte nicht geladen werden – Grauzone nutzt dann das andere Modell."
    fi
done

[ -f vornamen.txt ] || printf "Anni\nDirk\n" > vornamen.txt

echo "▶ Lade Texterkennungs-Modelle (EasyOCR, einmalig) …"
"$PY" -c "import easyocr; easyocr.Reader(['de', 'en'], gpu=False, verbose=False)" \
    || echo "⚠ EasyOCR-Modelle werden beim ersten Start nachgeladen."

trap - ERR
echo ""
echo "✅ Einrichtung abgeschlossen."
echo "   Künftig reicht ein Doppelklick auf START_GRAUZONE.command."
echo ""

# --- 5. Starten -------------------------------------------------------------
echo "▶ Starte Grauzone … (Browser öffnet http://localhost:8501)"
echo "   Beenden: dieses Fenster schließen oder ctrl+C drücken."
# Browser öffnen, sobald Grauzone antwortet
( for _ in $(seq 1 120); do
    curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health && { open "http://localhost:8501"; break; }
    sleep 1
  done ) &
exec "$PY" -m streamlit run app.py
