# Übergabe: Grauzone PRO

Stand: 11.11.2026, Version **0.4.5** (Release `v0.4.5` noch nicht veröffentlicht; zuletzt veröffentlicht: `v0.4.4`; `v0.3.1` nur als Tag)

Dieses Dokument fasst zusammen, wie das Projekt aufgebaut ist, wie man eine neue Version herausbringt und was noch offen ist. Für Nutzerinnen und Nutzer ist die [README](README.md) gedacht.

---

## 1. Worum es geht

Grauzone PRO schwärzt personenbezogene Daten in PDF-Dokumenten, vollständig lokal. Oberfläche: Streamlit im Browser unter `http://localhost:8501`, nur auf dem eigenen Rechner erreichbar.

| Baustein | Aufgabe |
|---|---|
| PyMuPDF (`import pymupdf`) | PDF lesen, Wortpositionen aus der Textebene, Schwärzen (`apply_redactions`) |
| EasyOCR | Texterkennung für gescannte Seiten (wortweise, `width_ths=0.05`) |
| spaCy 3.5 + `de_core_news_lg`/`_sm` | Personen, Orte, Organisationen |
| Streamlit | Oberfläche |

## 2. Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Oberfläche: Hochladen, Scannen (Seite / alle Seiten), Fundstellen-Liste, Lernen, Export |
| `erkennung.py` | Erkennung ohne Streamlit: Wörter holen, Seitentext bauen, Fundstellen suchen, Rechtecke berechnen, Markdown-Export (`markdown`) |
| `requirements.txt` | Bibliotheken; **spaCy < 3.6 und numpy < 2 sind Pflicht**; Streamlit auf getestete Versionen begrenzt (`>=1.50,<1.68`); PyMuPDF je nach Python: 2.1.x ab 3.11, sonst 1.26.x |
| `.streamlit/config.toml` | nur `localhost`, keine Nutzungsstatistik, `headless` (keine E-Mail-Abfrage) |
| `Grauzone installieren.command` | Einrichtung aus dem Quellcode per Doppelklick (uv + Python 3.11) |
| `START_GRAUZONE.command`, `starten.command` | Start nach der Einrichtung |
| `setup_project.py` | Einrichtung für den Weg über das Terminal |
| `macos/` | Mac-App: Starter, Einrichtungsskript, Icon, `build_dmg.sh`, `VERSION` |

Lokale Daten (nicht im Repository): `knowledge_base.json` (gelernte Begriffe: `blacklist` = immer schwärzen, `whitelist` = nie schwärzen), `vornamen.txt`.

## 3. Wie die Mac-App funktioniert

Die DMG (~470 KB) enthält nur einen Starter, keine Bibliotheken.

1. `Grauzone PRO.app/Contents/MacOS/Grauzone` (= `macos/Grauzone-launcher.sh`) kopiert `app.py`, `erkennung.py`, `requirements.txt`, `VERSION`, `grauzone-update.sh` und die Streamlit-Einstellungen nach `~/Library/Application Support/Grauzone PRO` (per `cat`, damit kein Quarantäne-Attribut mitkommt), aber nur, wenn die Version der App neuer ist als die im Datenordner. Dann öffnet er dort `Grauzone starten.command` im Terminal.
2. `Grauzone starten.command` ruft zuerst `grauzone-update.sh` (= `macos/grauzone-update.sh`) auf: Selbst-Update, siehe unten.
3. `Grauzone starten.command` (= `macos/grauzone-start.sh`) richtet beim ersten Start oder nach einer Änderung an `VERSION`/`requirements.txt` alles ein: uv, Python 3.11, Bibliotheken, spaCy-Modelle, EasyOCR-Modelle (~2 GB). Merker: Datei `.eingerichtet` mit Prüfsumme.
4. Danach startet Streamlit; ein Hintergrundprozess öffnet den Browser, sobald `/_stcore/health` antwortet. Terminalfenster schließen = Grauzone beenden.

Die App ist nur ad hoc signiert, nicht notarisiert. macOS fragt beim ersten Öffnen nach (Rechtsklick → Öffnen bzw. „Dennoch öffnen“).

**Selbst-Update (ab 0.4.0):** `grauzone-update.sh` liest `https://github.com/dirkblauhut/grauzone_pro/releases/latest/download/VERSION`. Ist diese Version neuer, fragt es im Terminal nach (`[j/N]`, nach 120 s „nein“). Bei „j“ lädt es `grauzone-update.tar.gz` und `SHA256SUMS` des Releases, prüft Prüfsumme, Vollständigkeit und Versionsangabe und ersetzt die Dateien per `mv`. Mit Rückgabe 10 startet sich das Startskript in der neuen Fassung neu. Per `curl` geladene Dateien tragen kein Quarantäne-Kennzeichen, eine neue Freigabe in macOS entfällt. Abschalten: Schalter in der Seitenleiste (legt `.keine-updatepruefung` im Datenordner an). Zum Testen lässt sich die Quelle mit der Umgebungsvariable `GRAUZONE_UPDATE_URL` auf einen lokalen Server umlenken. Der Starter in der .app selbst wird nur über eine neue DMG aktualisiert.

## 4. Neue Version herausbringen

1. Änderungen machen und testen (siehe Abschnitt 5).
2. Versionsnummer in `macos/VERSION` erhöhen. Dadurch prüft die App beim nächsten Start ihre Einrichtung neu.
3. Neue Dateien, die die App braucht, in `macos/Grauzone-launcher.sh` (Kopierschleife), `macos/build_dmg.sh` (`cp … Resources/grauzone/` **und** Update-Paket) sowie in `macos/grauzone-update.sh` (`DATEIEN` und Ersetzen) eintragen.
4. `sh macos/build_dmg.sh` → in `dist/`: `Grauzone-PRO-<Version>.dmg`, `grauzone-update.tar.gz`, `SHA256SUMS`, `VERSION` (der Ordner `dist/` wird nicht eingecheckt).
5. Commit, Tag `v<Version>` setzen, beides pushen.
6. Release mit **allen vier** Dateien anlegen und als neuestes markieren, z. B. `gh release create v<Version> dist/Grauzone-PRO-<Version>.dmg dist/grauzone-update.tar.gz dist/SHA256SUMS dist/VERSION --title "Grauzone PRO <Version>" --notes-file <Datei> --latest`. Ohne `VERSION`, Paket und Prüfsumme findet das Selbst-Update die Version nicht. Die README verlinkt immer auf `releases/latest`.

## 5. Testen

- **Automatische Tests:** `./venv/bin/python -m unittest discover -s tests` (wenige Sekunden). Mit `GRAUZONE_OCR_TEST=1` davor läuft zusätzlich der Scan-Test mit Texterkennung (etwa 30 s). Die Tests erzeugen ihre PDFs selbst aus erfundenen Daten.
- **Erkennung ohne Oberfläche:** `erkennung.py` lässt sich direkt mit PyMuPDF, spaCy und EasyOCR aufrufen (`woerter_aus_textebene` / `woerter_aus_ocr` → `seitentext` → `finde` → `wort_rechteck`). Danach `apply_redactions()` und mit `page.get_text()` prüfen, dass an den geschwärzten Stellen kein Text mehr steht.
- **Scan-Fall:** Testseite als Bild in ein neues PDF einfügen (ohne Textebene) und das Ergebnis als Bild ansehen: Es dürfen keine Buchstabenreste neben den Balken stehen.
- **App:** Datenordner mit einem eigenen `HOME` testen, damit der echte `~/Library/Application Support/Grauzone PRO` unberührt bleibt.
- Nur erfundene Testdaten verwenden (z. B. „Erika Mustermann, Musterstadt“).

## 6. Bekannte Fallstricke

- `python -m spacy download …` funktioniert mit spaCy 3.5 nicht mehr (Link mit Fehler 404). Modelle direkt als Wheel installieren: `https://github.com/explosion/spacy-models/releases/download/<modell>-3.5.0/<modell>-3.5.0-py3-none-any.whl`.
- spaCy 3.5 läuft nur mit Python bis 3.11 und nur mit numpy 1.x.
- Streamlit entfernt abgekündigte Optionen auch innerhalb von 1.x (z. B. `use_container_width`). Deshalb sind Streamlit und PyMuPDF in `requirements.txt` nach oben begrenzt (PyMuPDF 2.x braucht Python 3.11, daher zwei Zeilen mit `python_version`); die Grenze erst anheben, wenn die App mit der neuen Version getestet ist. Abkündigungen erscheinen als Warnung im Terminalfenster.
- Die gewählte Seite liegt in `st.session_state.seite` (Schlüssel des Seitenzahl-Feldes). Pfeile und „Bearbeiten“ ändern sie per `on_click`, weil Streamlit den Wert eines Widgets nach dessen Anzeige im selben Durchlauf nicht mehr ändern lässt.
- Ohne `headless = true` wartet Streamlit beim allerersten Start im Terminal auf eine E-Mail-Eingabe.
- Ohne `address = "localhost"` ist Streamlit im ganzen Netzwerk erreichbar und fragt die öffentliche IP-Adresse ab.
- Streamlit löscht den Zustand von Widgets, die gerade nicht angezeigt werden. Die Auswahl je Seite liegt deshalb in `st.session_state.auswahl`, nicht nur in den Checkboxen.
- `apply_redactions()` entfernt nur Seiteninhalt. Werte von Formularfeldern und Anmerkungen blieben bis 0.3.0 lesbar über den Balken stehen. `oeffne_pdf()` in `app.py` übernimmt sie deshalb vor Scan und Export mit `doc.bake()` fest in die Seite.
- Läuft beim Öffnen der App noch ein Grauzone-Server, nutzte der Starter bis 0.3.1 einfach diesen, auch nach einem Update. Seit 0.3.2 vergleicht `macos/Grauzone-launcher.sh` die `VERSION` und beendet einen älteren Server. Welche Version läuft, zeigt die Seitenleiste.

## 7. Offene Punkte

- **Bei Scans etwas breitere Balken:** EasyOCR kennt Wortgrenzen nur ungefähr. Anteilig geschätzte Wortteile bekommen viel Rand, dabei verschwindet manchmal ein Buchstabe des Nachbarworts.
- **Mehrseitige echte Dokumente** sind noch nicht getestet, ebenso **Windows** und der Gatekeeper-Dialog nach einem echten Download.
- **Gelernte „nie schwärzen“-Begriffe** gelten überall. Ein versehentlich abgewähltes Wort (z. B. ein Nachname, seit 0.6.0 auch eine Diagnose oder Kennnummer) wird danach in allen Dokumenten übersehen, bis man es wieder anhakt, mit ↶ zurücknimmt oder das Gedächtnis löscht.
- **Unterschriften, Fotos, Stempel, Handschrift** lassen sich nicht schwärzen, weil sie kein Text sind (geplant: Bereich von Hand schwärzen).
- **Lange Dokumente:** Die Texterkennung dauert etwa 15 bis 20 Sekunden pro Scan-Seite auf der CPU.
- **Notarisierung** bräuchte ein Apple-Entwicklerkonto (99 €/Jahr).
- **Lizenz:** Grauzone steht unter MIT. PyMuPDF steht unter AGPL. Solange die Bibliotheken bei der Einrichtung geladen und nicht mitgeliefert werden, ist das unproblematisch; beim PyInstaller-Weg nicht.

## 8. Verlauf

| Version | Datum | Inhalt |
|---|---|---|
| 0.1.0 / 0.1.1 | 18.05.2026 | erste Fassung, Schwärzung ganzer OCR-Zeilen |
| 0.2.0 | 11.11.2026 | Installation per Doppelklick, Mac-App als DMG mit Icon, MIT-Lizenz, Streamlit nur lokal, Modell-Download repariert |
| 0.3.0 | 11.11.2026 | Schwärzung auf Wortebene, mehr Muster, alle Seiten, Begriffe ergänzen, Metadaten entfernen |
| 0.3.1 | 11.11.2026 | Formularfelder und Anmerkungen werden mitgeschwärzt (vorher blieb ihr Text lesbar) |
| 0.3.2 | 11.11.2026 | Starter beendet nach einem Update einen noch laufenden alten Server; Versionsnummer in der Seitenleiste |
| 0.4.0 | 11.11.2026 | Selbst-Update von GitHub nach Rückfrage, abschaltbar in der Seitenleiste |
| 0.4.1 | 11.11.2026 | Export zusätzlich als Markdown mit nummerierten Platzhaltern |
| 0.4.2 | 11.11.2026 | `use_container_width` durch `width="stretch"` ersetzt, Streamlit-Version begrenzt |
| 0.4.3 | 11.11.2026 | `import pymupdf` statt `import fitz`, PyMuPDF-Version begrenzt |
| 0.4.4 | 11.11.2026 | Vorschau zeigt alle Seiten zum Scrollen, Blättern mit ◀ ▶ und „Bearbeiten“ |
| 0.4.5 | 11.11.2026 | ◀ ▶, Seitenzahl und Schalter scrollen die Vorschau zur Seite; Scrollbereich passt sich der Fensterhöhe an |
| 0.4.6 | 12.11.2026 | Erkennung: Name über Zeilenumbruch nach Anrede, Name nach Feldbezeichnung („Absender:“), E-Mail und IBAN auch bei OCR-Fehlern auf Scan-Seiten |
| 0.4.7 | 12.11.2026 | Export entfernt zusätzlich XMP-Metadaten, Lesezeichen und eingebettete Dateien, prüft das fertige PDF (Text und Helligkeit unter den Balken, Metadaten, Anmerkungen, Formularfelder); Schaltfläche „Beenden“ |
| 0.5.0 | 12.11.2026 | Neue Oberfläche in drei Spalten mit Kopfzeile, Fundstellenkarten und Filter, Seitenübersicht, Prüfprotokoll als Markdown-Download ohne Originaldaten, Symbol der App im Browser, „Beenden“ ohne Fehlerdialog; Regressionstests |
| 0.5.1 | 12.11.2026 | Fundstellenliste erscheint nach dem Scannen sofort, nicht erst nach dem Zeichnen aller Vorschauseiten |
| 0.5.2 | 12.11.2026 | Dateinamen des Exports ohne Namen des Originaldokuments (`<Datum>_<Uhrzeit>_Anonymisiert.pdf`/`.md`, `…_Pruefprotokoll.md`); EasyOCR auf 1.7.x begrenzt |
| 0.6.0 | 12.11.2026 | Begründung je Fundstelle, Prüfwarteschlange (zu prüfen vor eindeutig), IBAN-Prüfziffer, Suche, „Alle schwärzen/freigeben“ ohne Lernen, Ansicht Original/Ergebnis/Beide, gleiche Angaben gemeinsam entscheiden, Rückgängig/Wiederholen, Export einzelner Seiten; Erkennung von Kennnummern (mit Prüfziffer), Geburtsdatum nur mit Kontext und Gesundheitsangaben |
