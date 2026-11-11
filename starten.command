#!/bin/bash
cd -- "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then
    echo "Grauzone ist auf diesem Rechner noch nicht eingerichtet."
    echo "Bitte zuerst \"Grauzone installieren.command\" doppelklicken."
    read -r -p "[Enter] drücken …" _
    exit 1
fi
exec ./venv/bin/python -m streamlit run app.py
