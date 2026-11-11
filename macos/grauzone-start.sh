#!/bin/bash
# Wird von "Grauzone PRO.app" nach ~/Library/Application Support/Grauzone PRO
# kopiert und im Terminal geöffnet. Richtet beim ersten Start (und nach einem
# Update) alles ein und startet dann Grauzone im Browser.

cd -- "$(dirname "$0")"
printf '\033]0;Grauzone PRO\007'   # Fenstertitel

fehler() {
    echo ""
    echo "❌ Einrichtung abgebrochen: $1"
    echo "   Bitte Internetverbindung prüfen und Grauzone erneut öffnen."
    read -r -p "   [Enter] drücken …" _
    exit 1
}

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# Nach neuer Version suchen (fragt vorher nach, abschaltbar). Nach einem
# Update dieses Skript in seiner neuen Fassung erneut starten.
if [ -f grauzone-update.sh ]; then
    bash ./grauzone-update.sh
    [ $? -eq 10 ] && exec bash "$0"
fi

PY="$(pwd)/venv/bin/python"
STAND="$(cat VERSION requirements.txt | shasum | cut -d' ' -f1)"

if [ "$(cat .eingerichtet 2>/dev/null)" != "$STAND" ] || [ ! -x "$PY" ]; then
    set -e
    trap 'fehler "unerwarteter Fehler in Zeile $LINENO (siehe Meldungen oben)."' ERR
    echo "=== Grauzone PRO – Einrichtung ==="
    echo "Beim ersten Start dauert das 5–15 Minuten (ca. 2 GB Download)."
    echo "Danach startet Grauzone in wenigen Sekunden und arbeitet offline."
    echo ""

    if ! command -v uv >/dev/null 2>&1; then
        echo "▶ Installiere Hilfsprogramm uv (astral.sh) …"
        curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh \
            || fehler "uv konnte nicht geladen werden."
    fi

    if ! { [ -x "$PY" ] && "$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; }; then
        rm -rf venv
        echo "▶ Lege Python-3.11-Umgebung an …"
        uv venv --python 3.11 venv
    fi

    echo "▶ Installiere Bibliotheken (u. a. PyTorch, spaCy, Streamlit) …"
    uv pip install --python "$PY" -r requirements.txt

    for modell in de_core_news_sm de_core_news_lg; do
        if ! "$PY" -c "import spacy.util, sys; sys.exit(0 if spacy.util.is_package('$modell') else 1)"; then
            echo "▶ Lade Sprachmodell $modell …"
            uv pip install --python "$PY" \
                "https://github.com/explosion/spacy-models/releases/download/$modell-3.5.0/$modell-3.5.0-py3-none-any.whl"
        fi
    done

    echo "▶ Lade Texterkennungs-Modelle (EasyOCR) …"
    "$PY" -W ignore -c "import easyocr; easyocr.Reader(['de', 'en'], gpu=False, verbose=False)"

    echo "$STAND" > .eingerichtet
    trap - ERR
    set +e
    echo ""
    echo "✅ Einrichtung abgeschlossen."
    echo ""
fi

[ -f vornamen.txt ] || printf "Anni\nDirk\n" > vornamen.txt

echo "▶ Grauzone PRO läuft unter http://localhost:8501"
echo "   Beenden: dieses Fenster schließen."
echo "   Daten (Wissensbasis, Vornamenliste): $(pwd)"
echo ""
# Browser öffnen, sobald Grauzone antwortet
( for _ in $(seq 1 120); do
    curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health && { open "http://localhost:8501"; break; }
    sleep 1
  done ) &
exec "$PY" -m streamlit run app.py
