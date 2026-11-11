#!/bin/bash
# Baut "Grauzone PRO.app" und verpackt sie als DMG.
#
#   sh macos/build_dmg.sh            -> dist/Grauzone-PRO-<Version>.dmg (als Release-Anhang hochladen)
#
# Voraussetzung: macOS (sips, iconutil, hdiutil). Das Icon liegt fertig als
# macos/icon_1024.png vor; neu zeichnen mit  python macos/make_icon.py macos/icon_1024.png

set -euo pipefail
cd -- "$(dirname "$0")/.."

VERSION="$(cat macos/VERSION)"
NAME="Grauzone PRO"
BAU="build/dmg"
APP="$BAU/inhalt/$NAME.app"
ZIEL="dist/Grauzone-PRO-$VERSION.dmg"

rm -rf "$BAU"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/grauzone" dist

# --- Icon -------------------------------------------------------------------
SET="$BAU/AppIcon.iconset"
mkdir -p "$SET"
for g in 16 32 128 256 512; do
    sips -z $g $g macos/icon_1024.png --out "$SET/icon_${g}x${g}.png" >/dev/null
    sips -z $((g * 2)) $((g * 2)) macos/icon_1024.png --out "$SET/icon_${g}x${g}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$APP/Contents/Resources/AppIcon.icns"

# --- App-Bundle ------------------------------------------------------------
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>               <string>$NAME</string>
    <key>CFBundleDisplayName</key>        <string>$NAME</string>
    <key>CFBundleIdentifier</key>         <string>de.blaumuetze.grauzone</string>
    <key>CFBundleVersion</key>            <string>$VERSION</string>
    <key>CFBundleShortVersionString</key> <string>$VERSION</string>
    <key>CFBundleExecutable</key>         <string>Grauzone</string>
    <key>CFBundleIconFile</key>           <string>AppIcon</string>
    <key>CFBundlePackageType</key>        <string>APPL</string>
    <key>LSMinimumSystemVersion</key>     <string>12.0</string>
    <key>NSHumanReadableCopyright</key>   <string>© 2026 Dirk Blauhut · MIT-Lizenz</string>
</dict>
</plist>
EOF
cp macos/Grauzone-launcher.sh "$APP/Contents/MacOS/Grauzone"
cp macos/grauzone-start.sh "$APP/Contents/Resources/grauzone-start.sh"
chmod +x "$APP/Contents/MacOS/Grauzone" "$APP/Contents/Resources/grauzone-start.sh"
cp app.py erkennung.py requirements.txt "$APP/Contents/Resources/grauzone/"
cp .streamlit/config.toml "$APP/Contents/Resources/grauzone/streamlit-config.toml"
cp macos/VERSION "$APP/Contents/Resources/grauzone/VERSION"
cp LICENSE "$APP/Contents/Resources/LICENSE"

# Ad-hoc-Signatur (kein Apple-Entwicklerzertifikat): macOS fragt beim ersten
# Öffnen trotzdem nach, die App bleibt aber in sich unverändert prüfbar.
codesign --force --deep --sign - "$APP" 2>/dev/null || true

# --- DMG-Inhalt ------------------------------------------------------------
ln -s /Applications "$BAU/inhalt/Programme"
cp LICENSE "$BAU/inhalt/Lizenz.txt"
cat > "$BAU/inhalt/Bitte lesen.txt" <<'EOF'
Grauzone PRO – lokale Schwärzung von PDF-Dokumenten

INSTALLIEREN
1. "Grauzone PRO" auf den Ordner "Programme" ziehen.
2. Grauzone PRO im Programme-Ordner öffnen.
   Meldet macOS, die App stamme von einem nicht verifizierten Entwickler:
   - macOS 14 und älter: Rechtsklick auf die App → "Öffnen" → "Öffnen".
   - macOS 15 und neuer: Systemeinstellungen → Datenschutz & Sicherheit →
     ganz unten bei "Grauzone PRO" auf "Dennoch öffnen" klicken.
3. Beim ersten Start öffnet sich ein Terminalfenster und lädt einmalig
   Python, Bibliotheken und KI-Modelle (ca. 2 GB, 5–15 Minuten).
   Danach öffnet sich Grauzone im Browser (http://localhost:8501).

BENUTZEN
- Starten: Grauzone PRO öffnen. Beenden: das Terminalfenster schließen.
- Alles läuft lokal. Internet wird nur für die Einrichtung gebraucht.

DATEN UND ENTFERNEN
Python-Umgebung, Wissensbasis (knowledge_base.json) und Vornamenliste
(vornamen.txt) liegen in:
  ~/Library/Application Support/Grauzone PRO
Zum vollständigen Entfernen die App und diesen Ordner löschen.

Quellcode: https://github.com/dirkblauhut/grauzone_pro
EOF

# --- DMG bauen ---------------------------------------------------------------
cp "$APP/Contents/Resources/AppIcon.icns" "$BAU/inhalt/.VolumeIcon.icns"
rm -f "$BAU/roh.dmg" "$ZIEL"
hdiutil create -quiet -volname "$NAME" -srcfolder "$BAU/inhalt" -fs HFS+ -format UDRW "$BAU/roh.dmg"
MOUNT="$(hdiutil attach -nobrowse -noautoopen "$BAU/roh.dmg" | awk -F'\t' '/\/Volumes\//{print $NF}')"
SetFile -a C "$MOUNT" 2>/dev/null || true       # Volume-Icon aktivieren
hdiutil detach -quiet "$MOUNT"
hdiutil convert -quiet "$BAU/roh.dmg" -format UDZO -imagekey zlib-level=9 -o "$ZIEL"
rm -rf "$BAU"

echo "Fertig: $ZIEL ($(du -h "$ZIEL" | cut -f1))"
