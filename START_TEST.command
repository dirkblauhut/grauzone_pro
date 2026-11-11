#!/bin/bash
# Startet die Testversion (Branch "redesign") aus dem Quellcode auf Port 8502.
# Die installierte Mac-App (Port 8501) kann gleichzeitig laufen; Wissensbasis
# und Vornamenliste liegen hier im Projektordner, getrennt von der App.
cd -- "$(dirname "$0")"
printf '\033]0;Grauzone TEST\007'   # Fenstertitel

if ! { [ -x venv/bin/python ] && venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; }; then
    echo "Auf diesem Rechner fehlt die Python-3.11-Umgebung (venv/)."
    echo "Bitte zuerst \"Grauzone installieren.command\" doppelklicken."
    read -r -p "[Enter] drücken …" _
    exit 1
fi

echo "▶ Grauzone TEST (Branch $(git branch --show-current 2>/dev/null)) unter http://localhost:8502"
echo "   Beenden: dieses Fenster schließen."
echo ""
# Browser öffnen, sobald die Testversion antwortet
( for _ in $(seq 1 120); do
    curl -fs -m 1 -o /dev/null http://localhost:8502/_stcore/health && { open "http://localhost:8502"; break; }
    sleep 1
  done ) &
exec ./venv/bin/python -m streamlit run app.py --server.port 8502
