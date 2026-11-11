#!/bin/bash
# Programmdatei von "Grauzone PRO.app" (Contents/MacOS/Grauzone).
#
# Die App selbst ist nur ein Starter: Sie kopiert die Programmdateien nach
#   ~/Library/Application Support/Grauzone PRO
# (dort liegen auch Python-Umgebung, Wissensbasis und Vornamenliste) und
# öffnet ein Terminalfenster, das beim ersten Mal alles einrichtet und dann
# Grauzone im Browser startet. Fenster schließen = Grauzone beenden.

RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
DATA="$HOME/Library/Application Support/Grauzone PRO"
mkdir -p "$DATA/.streamlit"

# Läuft Grauzone schon? Dann nur den Browser nach vorn holen.
if curl -fs -m 2 -o /dev/null http://localhost:8501/_stcore/health; then
    open "http://localhost:8501"
    exit 0
fi

# Programmdateien aktualisieren. Bewusst per "cat" statt "cp", damit das
# Quarantäne-Attribut des Downloads nicht mitkopiert wird.
for f in app.py erkennung.py requirements.txt VERSION; do
    cat "$RES/grauzone/$f" > "$DATA/$f"
done
cat "$RES/grauzone/streamlit-config.toml" > "$DATA/.streamlit/config.toml"
cat "$RES/grauzone-start.sh" > "$DATA/Grauzone starten.command"
chmod +x "$DATA/Grauzone starten.command"

open -a Terminal "$DATA/Grauzone starten.command"
