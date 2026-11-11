#!/bin/bash
# Programmdatei von "Grauzone PRO.app" (Contents/MacOS/Grauzone).
#
# Die App selbst ist nur ein Starter: Sie kopiert die Programmdateien nach
#   ~/Library/Application Support/Grauzone PRO
# (nur wenn sie neuer sind; spätere Versionen lädt grauzone-update.sh selbst)
# (dort liegen auch Python-Umgebung, Wissensbasis und Vornamenliste) und
# öffnet ein Terminalfenster, das beim ersten Mal alles einrichtet und dann
# Grauzone im Browser startet. Fenster schließen = Grauzone beenden.

RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
DATA="$HOME/Library/Application Support/Grauzone PRO"
mkdir -p "$DATA/.streamlit"

neuer() {   # neuer A B: ist Version A neuer als B?
    [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]
}
laeuft() { curl -fs -m 1 -o /dev/null http://localhost:8501/_stcore/health; }

# Programmdateien aus der App nur übernehmen, wenn sie neuer sind als die im
# Datenordner. Die Version im Datenordner kann durch das Selbst-Update
# (grauzone-update.sh) schon neuer sein als die der App; dann bleibt sie.
APP_VERSION="$(tr -d '[:space:]' < "$RES/grauzone/VERSION")"
DATA_VERSION="$(tr -d '[:space:]' 2>/dev/null < "$DATA/VERSION")"
if [ ! -f "$DATA/app.py" ] || [ ! -f "$DATA/grauzone-update.sh" ] || neuer "$APP_VERSION" "$DATA_VERSION"; then
    UEBERNEHMEN=1
else
    UEBERNEHMEN=0
fi

# Läuft Grauzone schon? Ohne neue Programmdateien nur den Browser nach vorn
# holen. Sonst den alten Server beenden, damit nicht der alte Code weiterläuft.
if laeuft; then
    if [ "$UEBERNEHMEN" = 0 ]; then
        open "http://localhost:8501"
        exit 0
    fi
    pkill -f "$DATA/venv/bin/python -m streamlit"
    for _ in $(seq 1 20); do
        laeuft || break
        sleep 0.5
    done
    if laeuft; then
        osascript -e 'display alert "Grauzone PRO" message "Eine ältere Grauzone läuft noch. Bitte deren Terminalfenster schließen und Grauzone PRO erneut öffnen."'
        exit 1
    fi
fi

# Bewusst per "cat" statt "cp", damit das Quarantäne-Attribut des Downloads
# nicht mitkopiert wird.
if [ "$UEBERNEHMEN" = 1 ]; then
    for f in app.py erkennung.py requirements.txt VERSION grauzone-update.sh; do
        cat "$RES/grauzone/$f" > "$DATA/$f"
    done
    cat "$RES/grauzone/streamlit-config.toml" > "$DATA/.streamlit/config.toml"
    cat "$RES/grauzone-start.sh" > "$DATA/Grauzone starten.command"
    chmod +x "$DATA/Grauzone starten.command" "$DATA/grauzone-update.sh"
fi

open -a Terminal "$DATA/Grauzone starten.command"
