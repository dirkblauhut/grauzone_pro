#!/bin/bash
cd -- "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then
    echo "Grauzone ist auf diesem Rechner noch nicht eingerichtet."
    echo "Bitte zuerst \"Grauzone installieren.command\" doppelklicken."
    read -r -p "[Enter] drücken …" _
    exit 1
fi
# Browser öffnen, sobald Grauzone antwortet
( for _ in $(seq 1 120); do
    curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health && { open "http://localhost:8501"; break; }
    sleep 1
  done ) &
exec ./venv/bin/python -m streamlit run app.py
