#!/bin/bash
# Sucht beim Start nach einer neueren Grauzone-Version und installiert sie
# nach Rückfrage. Wird von "Grauzone starten.command" im Datenordner
# (~/Library/Application Support/Grauzone PRO) aufgerufen.
#
# Datenschutz: Es geht nur eine Anfrage nach der Versionsnummer an GitHub,
# keine Dokumentinhalte. Abschalten: Datei ".keine-updatepruefung" im
# Datenordner anlegen (Schalter in der Seitenleiste von Grauzone).
#
# Ablauf:
#   1. <QUELLE>/latest/download/VERSION lesen (Release-Anhang "VERSION").
#   2. Ist sie neuer als die installierte: nachfragen.
#   3. grauzone-update.tar.gz und SHA256SUMS des Releases laden, Prüfsumme
#      und Inhalt prüfen, Dateien ersetzen.
# Per curl geladene Dateien tragen kein Quarantäne-Kennzeichen; macOS
# verlangt daher keine erneute Freigabe.
#
# Rückgabe: 10 = Update installiert (Startskript neu starten), sonst 0.

cd -- "$(dirname "$0")" || exit 0
QUELLE="${GRAUZONE_UPDATE_URL:-https://github.com/dirkblauhut/grauzone_pro/releases}"
DATEIEN="app.py erkennung.py requirements.txt VERSION streamlit-config.toml grauzone-start.sh grauzone-update.sh"

[ -f .keine-updatepruefung ] && exit 0

neuer() {   # neuer A B: ist Version A neuer als B?
    [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]
}

HIER="$(tr -d '[:space:]' 2>/dev/null < VERSION)"
NEU="$(curl -fsSL -m 5 "$QUELLE/latest/download/VERSION" 2>/dev/null | tr -d '[:space:]')"
[[ "$NEU" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] || exit 0    # offline oder keine Angabe
neuer "$NEU" "$HIER" || exit 0

echo "▶ Neue Version $NEU verfügbar (installiert: ${HIER:-unbekannt})."
echo "   Änderungen: $QUELLE/tag/v$NEU"
read -r -t 120 -p "   Jetzt installieren? [j/N] " antwort || antwort=""
echo ""
case "$antwort" in
    j|J|ja|Ja|JA) ;;
    *) echo "   Übersprungen. Beim nächsten Start wird erneut gefragt."; echo ""; exit 0 ;;
esac

abbruch() {
    echo "⚠ Update abgebrochen: $1"
    echo "   Grauzone startet mit Version ${HIER:-unbekannt}."
    echo ""
    exit 0
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "▶ Lade Version $NEU …"
curl -fsSL -m 120 -o "$TMP/grauzone-update.tar.gz" "$QUELLE/download/v$NEU/grauzone-update.tar.gz" \
    && curl -fsSL -m 30 -o "$TMP/SHA256SUMS" "$QUELLE/download/v$NEU/SHA256SUMS" \
    || abbruch "Download fehlgeschlagen."
( cd "$TMP" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1 ) || abbruch "Prüfsumme stimmt nicht."
mkdir "$TMP/neu"
tar -xzf "$TMP/grauzone-update.tar.gz" -C "$TMP/neu" 2>/dev/null || abbruch "Paket beschädigt."
for f in $DATEIEN; do
    [ -s "$TMP/neu/$f" ] || abbruch "Datei $f fehlt im Paket."
done
[ "$(tr -d '[:space:]' < "$TMP/neu/VERSION")" = "$NEU" ] || abbruch "Versionsangabe im Paket passt nicht."

# Ersetzen per mv: Das laufende Startskript behält so seine alte Datei.
mkdir -p .streamlit
for f in app.py erkennung.py requirements.txt VERSION grauzone-update.sh; do
    mv -f "$TMP/neu/$f" "$f"
done
mv -f "$TMP/neu/streamlit-config.toml" .streamlit/config.toml
mv -f "$TMP/neu/grauzone-start.sh" "Grauzone starten.command"
chmod +x "Grauzone starten.command" grauzone-update.sh

echo "✅ Version $NEU installiert."
echo ""
exit 10
