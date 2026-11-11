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

# Läuft Grauzone schon? Gleiche Version: nur den Browser nach vorn holen.
# Ältere Version (nach einem Update): alten Server beenden, sonst liefe
# weiter der alte Programmcode.
if curl -fs -m 2 -o /dev/null http://localhost:8501/_stcore/health; then
    if cmp -s "$RES/grauzone/VERSION" "$DATA/VERSION"; then
        open "http://localhost:8501"
        exit 0
    fi
    pkill -f "$DATA/venv/bin/python -m streamlit"
    for _ in $(seq 1 20); do
        curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health || break
        sleep 0.5
    done
    if curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health; then
        osascript -e 'display alert "Grauzone PRO" message "Eine ältere Grauzone läuft noch. Bitte deren Terminalfenster schließen und Grauzone PRO erneut öffnen."'
        exit 1
    fi
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
