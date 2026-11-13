# Projektstand: Grauzone PRO

Stand: 2026-11-13, Branch main, Version 0.6.0 (0.5.0 und 0.5.1 vom Nutzer veröffentlicht, 0.5.2 und 0.6.0 aus der lokalen Sitzung auf dem Mac)

Ergänzt [UEBERGABE.md](UEBERGABE.md). Dort stehen Dateiübersicht, Funktionsweise der Mac-App, Release-Ablauf (Abschnitt 4) und Testanleitung (Abschnitt 5). Diese Datei hält Festlegungen, Learnings und Sackgassen fest und wird nicht mit UEBERGABE.md zusammengeführt.

## Verbindlichkeit

Abschnitt 1 (Festlegungen) und Abschnitt 3 beschreiben abgestimmte und getestete Lösungen. Sie werden nicht geändert, zurückgebaut oder umgebaut, solange keine neue Anforderung das verlangt. Verlangt eine neue Funktion eine Änderung, vor der Umsetzung die betroffene Festlegung benennen, die Änderung begründen und Rückfrage halten.

## Oberfläche und Arbeitsweise (seit 0.5.0)

Vom Nutzer festgelegt am 2026-11-12: Die Testversion der neuen Oberfläche war erfolgreich und ist mit 0.5.0 in `main` aufgegangen. Der Branch `redesign` und `START_TEST.command` (Port 8502) entfallen; gearbeitet wird nur noch auf `main`, auf beiden Macs per `git pull` und `git push`.
- Releases nur aus `main`, wie in UEBERGABE.md, Abschnitt 4.
- Pro Gerät, nicht im Repository: `venv/` (per `Grauzone installieren.command`), `knowledge_base.json`, `vornamen.txt`.
- Aufbau (nach Bild 1 des ChatGPT-Entwurfs, vom Nutzer gewählt): Kopfzeile in Dunkelblau mit Symbol der Mac-App, Beenden-Schaltfläche und ⚙-Popover (Update-Schalter), drei Spalten ohne Seitenleiste: links Hochladen, Analyse (OCR, Scannen), Lernfortschritt, Seitenübersicht mit Vorschaubildern; Mitte Werkzeugleiste (◀ Seite ▶, Zoom −/+, „Alle Seiten“) und Vorschau; rechts Fundstellen als Karten mit Filter (Alle/Personen/Kontakte/Weitere), „Fehlt etwas?“, Export; Statuszeile unten. Stil per CSS in `app.py` (`STIL`) und `[theme]` in `.streamlit/config.toml`. Das Symbol (Browser-Tab und Kopfzeile) steckt als Base64 in `app.py` (`ICON_BASE64`, aus `macos/icon_1024.png`), damit keine zusätzliche Datei in die Mac-App und das Selbst-Update muss.
- „Beenden“ ersetzt vor dem Beenden des Servers die Browserseite durch eine feste deutsche Seite (Überlagerung per `components.html`); sonst zeigt Streamlit den englischen Dialog „Connection error“.
- Bewusst weggelassen, weil die Funktion fehlt: Konfidenz-Prozente, Smart-Learning, Profile. Prüfprotokoll seit 2026-11-12 umgesetzt: dritter Download „📋 Protokoll“ (Markdown, `E.pruefprotokoll`), mit Dateihash (SHA-256) statt Dateiname, Zahlen je Art (gefunden, geschwärzt, abgewählt), Quelle je Seite, Ergebnis der Exportprüfung; Dateiname `Pruefprotokoll_<Datum>_<Zeit>.md` ohne Dokumentnamen; Tests in `tests/test_export_pruefung.py` und `tests/test_app.py`. Das Markdown des Exports wird nicht gesondert geprüft (nur im Protokoll vermerkt).
- Paket A (Stand 2026-11-12, Version 0.6.0; vom Nutzer gewählt): Jede Fundstelle trägt ihre Quellen (`Fund.quellen`, Texte in `E.BEGRUENDUNG`), die Karte zeigt die Begründung. Prüfwarteschlange mit zwei Stufen statt Prozenten (`E.ist_eindeutig`): „zu prüfen“ (nur Sprachmodell, nur Vornamenliste, E-Mail aus Texterkennung, IBAN mit ungültiger Prüfziffer) vor „eindeutig“ (Anrede, Feldbezeichnung, Muster, gelernt, oder zwei verschiedene Quellen); Statuszeile nennt die Zahl zu prüfender Stellen je Seite. IBAN-Prüfziffer nach Modulo 97. Suche über die Fundstellen aller gescannten Seiten mit Sprung zur Seite und Hinweis, wenn der Begriff nur im Text steht. Sammelaktion „Alle schwärzen/freigeben“ für alle zu Filter und Suche passenden Fundstellen aller gescannten Seiten. Ansicht „Original | Ergebnis | Beide“ in der Werkzeugleiste: Ergebnis ist das mit `E.schwaerze` erzeugte PDF zur aktuellen Auswahl (`ergebnis_doc`, neu nur bei geänderten Balken). Tests: Klasse `Begruendung` in `tests/test_erkennung.py`, vier App-Tests in `tests/test_app.py`. Die Begründung erfasst keine Funktionsbezeichnungen und keine Kombination mehrerer Angaben (zurückgestellt).
- Paket B (Stand 2026-11-12, Version 0.6.0; vom Nutzer gewählt): Schalter „Gleiche Angaben gemeinsam entscheiden“ (Analyse-Karte, Vorgabe an): ein Haken von Hand gilt für dieselbe Angabe auf allen gescannten Seiten (Vergleich ohne Groß-/Kleinschreibung und Leerraum, `gleich`); die Karte nennt „auch auf Seite …“. Rückgängig/Wiederholen (↶ ↷ in der Werkzeugleiste, je bis 50 Schritte, Hilfetext nennt den Schritt): Zustand ist Auswahl **und** Wissensbasis, damit auch Gelerntes zurückgenommen wird; erfasst Haken, Sammelaktion, „Fehlt etwas?“ und „Gedächtnis löschen“; Verlauf wird bei neuer Datei geleert. Export einzelner Seiten: Feld „Seiten“ in der Export-Karte (`E.seitenauswahl`, z. B. „1-3, 5“, leer = alle); `E.schwaerze(..., seiten)` wählt die Seiten nach dem Schwärzen aus, `E.pruefe_export(..., nummern)` meldet Seitenzahlen des Originals, Protokoll und Markdown nennen die exportierten Seiten. Wiederkehrende Textpassagen (Briefkopf, Fußzeile) und Export ausgewählter Bereiche sind nicht enthalten. Tests: Klasse `EinzelneSeiten` in `tests/test_export_pruefung.py`, vier App-Tests.
- Paket C (Stand 2026-11-12, Version 0.6.0; Vorlage: Erkennungskatalog des Nutzers für ein Sprachmodell, als Regeln umgesetzt). Festlegungen des Nutzers vom 2026-11-12: (1) Datum nur mit Kontext schwärzen („geb.“, „geboren am“, „Geburtsdatum:“), alle anderen Daten und Altersangaben nicht. (2) Von den kontextbezogenen Nummern nur Kunden-, Patienten- und Vertragsnummern; Aktenzeichen, Vorgangs- und Fallnummern bleiben lesbar. (3) Gesundheit: Diagnosen, Krankheiten, Medikamente, Behandlungen, Behinderungen. Umsetzung in `erkennung.py`: neue Arten `KENN` (Kennnummer), `GEB` (Geburtsdatum), `GES` (Gesundheit). Kennnummern nach Feldbezeichnung (`KENN_FELDER`: Kunden-, Patienten-, Vertrags-, Versicherungsnummer, Steuer-ID, Steuernummer, Renten-/Sozial- und Krankenversicherungsnummer, Ausweis, Pass, Führerschein, Konto, Kreditkarte, BIC, Kfz-Kennzeichen, IP-Adresse); Prüfziffern für Steuer-ID (ISO 7064), Rentenversicherungs-, Krankenversicherten-, Ausweisnummer und Kreditkarte (Luhn), geprüft an öffentlichen Musternummern. Ohne Feldbezeichnung nur Steuer-ID, RV-, KV-, Kreditkartennummer mit gültiger Prüfziffer und IP-Adressen (`FORMAT_MUSTER`), dann „zu prüfen“. Feld + gültige Prüfziffer oder Feld ohne bekannte Prüfziffer = eindeutig; Feld mit falscher Prüfziffer = zu prüfen. Gesundheit über Feldbezeichnung („Diagnose:“, „Medikation:“ … eindeutig), Wendungen („leidet an“, „wegen … in Behandlung“, „… diagnostiziert“; allein zu prüfen), Wortliste `GES_WOERTER` (allein zu prüfen) und ICD-10 nach „ICD“ (eindeutig). Filter: `GEB` unter Personen, `KENN` und `GES` unter Weitere. Nicht umgesetzt: indirekt identifizierende Kombinationen (nur mit Sprachmodell zuverlässig), „Ort ohne Personenbezug nicht markieren“ (Orte nur aus dem Sprachmodell stehen unter „zu prüfen“). Tests: Klassen `Kennnummern`, `Geburtsdatum`, `Gesundheit` in `tests/test_erkennung.py`, `Sensibel` in `tests/test_schwaerzung.py`.
- Vom Nutzer am 2026-11-12 abgelehnt, nicht wieder vorschlagen: Verwaltung oder Begrenzung der gelernten Ausnahmen (Whitelist bleibt global, keine Liste mit „Entfernen“). Ebenso abgelehnt (2026-11-12): mehrere Dokumente in einer Sitzung (wird nicht gebraucht).
- Ideen des Nutzers (ChatGPT-Entwurf vom 2026-11-11, nicht abgestimmt): Bearbeiten direkt im Dokument, Regeln mit Geltungsbereich (Dokument, Profil, global) und Rückfrage vor globaler Übernahme, Profile, Undo, Dark Mode optional. Vor der Umsetzung mit dem Nutzer klären, weil sie Festlegungen berühren: PDF.js als eigene Komponente (braucht Node/npm), Presidio und lokales Sprachmodell (Versionskette L2, 8 GB RAM), Tesseract statt EasyOCR (Systemprogramm), SQLite statt `knowledge_base.json`.

## 1. Kernarchitektur und Tech-Stack

Zweck: Personenbezogene Daten in PDF-Dokumenten vollständig lokal erkennen und physisch schwärzen.

Stack: Python 3.11 (Mac-App/Installer über uv), Streamlit, PyMuPDF (`import pymupdf`), EasyOCR, spaCy `>=3.5.0,<3.6.0` mit `de_core_news_lg` (Ersatz `de_core_news_sm`, je 3.5.0), `numpy<2`, Pillow, Faker. Streamlit `>=1.50,<1.68` (getestet: 1.67.0; `width=` geprüft ab 1.50). PyMuPDF `>=2.1,<2.2` ab Python 3.11, sonst `>=1.26.5,<1.27` (beide getestet). EasyOCR `>=1.7.2,<1.8` (getestet: 1.7.2, seit 2026-11-12 begrenzt).

Struktur:
- `app.py`: Streamlit-Oberfläche: Hochladen, Scannen (`scanne`, Seite oder alle Seiten), Fundstellenliste, Lernen über `knowledge_base.json`, Export über `E.schwaerze` (drei Spalten, siehe Abschnitt „Oberfläche und Arbeitsweise“).
- `erkennung.py`: Erkennung ohne Streamlit: `woerter_aus_textebene`, `woerter_aus_ocr`, `seitentext`, `finde`, `wort_rechteck`, `markdown` (Export), `oeffne_pdf`, `schwaerze` (physisches Schwärzen, Metadaten löschen; seit 0.5.0 aus `app.py` hierher verschoben); Datenklassen `Wort`, `Fund`.
- `tests/`: Regressionstests mit `unittest` (keine Zusatzbibliothek): `test_erkennung.py` (Muster, Grenzen, Rechtecke, Markdown), `test_schwaerzung.py` (mehrseitiges PDF, Formularfeld, Metadaten, Scan per OCR nur mit `GRAUZONE_OCR_TEST=1`), `test_app.py` (per `AppTest` in leerem Arbeitsordner: Start, Scannen, Blättern, Export, Haken entfernen); `hilfen.py` bildet `scanne` und Export ohne Streamlit nach.
- `.streamlit/config.toml`: `address = "localhost"`, `headless = true`, `gatherUsageStats = false`.
- `macos/`: `Grauzone-launcher.sh` (App-Starter), `grauzone-start.sh` (Einrichtung und Start im Datenordner), `grauzone-update.sh` (Selbst-Update), `build_dmg.sh`, `make_icon.py`, `VERSION`.
- `Grauzone installieren.command`, `START_GRAUZONE.command`, `starten.command`, `setup_project.py`: Einrichtung und Start aus dem Quellcode.
- Am 2026-11-12 entfernt (seit 0.3.0 nicht gepflegt, Wiederherstellung über die Git-Historie): `run_app.py`, `hooks/` (PyInstaller-Weg), `evaluate_system.py`, `generate_train_data.py`, `design.md`.

Datenfluss: Das PDF wird im Speicher geöffnet. `scanne` holt je Seite Wörter mit Position aus der Textebene; bei weniger als drei Wörtern oder erzwungener Texterkennung per EasyOCR. `finde` sucht im zusammengesetzten Seitentext Fundstellen (spaCy, Regex-Muster, Vornamenliste, Blacklist) und bildet sie auf Wörter ab. Beim Export schwärzt `wort_rechteck` nur die betroffenen Wortteile aller gescannten Seiten; nicht gescannte Seiten werden vorher gemeldet.

Festlegungen:
| Entscheidung | Begründung | Verworfene Alternative |
|---|---|---|
| Schwärzung auf Wortebene (`erkennung.py`) | Anrede und übriger Text bleiben lesbar (Commit b222dc7) | Ganze OCR-Zeilen schwärzen (0.1.x) |
| Textebene vor OCR, OCR nur als Ersatz oder erzwungen | Genaue Wortpositionen, schneller | Immer OCR (erste Fassung) |
| Physisches Schwärzen mit `apply_redactions()`, Metadaten löschen, `garbage=4` | Text unter Balken nicht kopierbar | Schwarze Rechtecke ohne Redaktion |
| spaCy 3.5.x, `numpy<2`, Python bis 3.11 | spaCy 3.5 ist nur so lauffähig | spaCy ohne Versionsgrenze |
| spaCy-Modelle als Wheel über feste GitHub-URL | `spacy download` liefert unter 3.5 Fehler 404 | `python -m spacy download`, Download zur Laufzeit in `load_nlp` (entfernt) |
| uv mit Python 3.11 in eigener `venv` | Systempython bleibt unberührt, reproduzierbar | Vorhandenes Python nutzen |
| DMG enthält nur Starter, Bibliotheken werden beim ersten Start geladen | Kleine DMG (~470 KB); PyMuPDF (AGPL) wird nicht mitgeliefert | PyInstaller-Bundle (`run_app.py`) |
| DMG nur als Release-Anhang, nicht im Repository | Commit a29a826 | `download/*.dmg` eingecheckt |
| Auswahl je Seite in `st.session_state.auswahl` | Streamlit verwirft Zustand nicht angezeigter Widgets | Auswahl nur in Checkboxen |
| Selbst-Update: `macos/grauzone-update.sh` liest Release-Anhang `VERSION`, lädt nach Rückfrage `grauzone-update.tar.gz`, prüft `SHA256SUMS`; Starter übernimmt Dateien aus der App nur, wenn sie neuer sind | Keine neue DMG und keine erneute Gatekeeper-Freigabe je Version | GitHub-API mit JSON (Rate-Limit, Parsing ohne Python); stilles Update ohne Rückfrage |
| Markdown-Export aus dem gespeicherten Seitentext und denselben Funden wie das PDF (`E.markdown`), Platzhalter `[Art Nr]` je Art und Text nummeriert | PDF und Markdown schwärzen dieselben Stellen; lesbarer als Balken | Text aus dem geschwärzten PDF lesen (Lücken ohne Kennzeichnung); `pymupdf4llm` (zusätzliche AGPL-Abhängigkeit) |
| Streamlit und PyMuPDF nach oben auf getestete Versionen begrenzen; `width="stretch"` statt `use_container_width`; `import pymupdf` statt `import fitz` | Abgekündigte Optionen und Namen können in neuen Versionen entfallen; ohne Grenze kann eine Neuinstallation brechen | Bibliotheken unbegrenzt lassen |
| Vorschau mit allen Seiten in einem scrollbaren Container, Fundstellen-Liste nur für die gewählte Seite (`st.session_state.seite`); Seitenbilder per `st.cache_data` (`seitenbild`), Funde je Seite in `st.session_state.funde_speicher` | Streamlit kennt die Scrollposition nicht; Zwischenspeicher hält das Neuzeichnen aller Seiten schnell. Seitenwechsel scrollt per `zur_seite_scrollen` (Skript über `components.html`, Marke `grauzone-seite-<p>`); Höhe per CSS an `100vh` (Container-Key `vorschau`) | Seitenwahl nur über Zahlenfeld (bis 0.4.3) |
| PDF immer über `oeffne_pdf()` öffnen (Formularfelder und Anmerkungen per `doc.bake()` in die Seite) | Nur so entfernt `apply_redactions()` auch deren Text; Scan und Export sehen denselben Inhalt | Formularfelder unverändert lassen; Felder nur löschen (verliert nicht betroffene Werte) |
| Lernen („nie schwärzen“) nur im `on_change` der Checkbox (`haken_geaendert`); Sammelaktionen (`sammelaktion`) setzen nur `st.session_state.auswahl` für dieses Dokument | Whitelist gilt global (vom Nutzer so belassen); eine Sammelfreigabe würde sonst mit einem Klick viele Begriffe dauerhaft freigeben | Lernen beim Zeichnen der Liste, wenn ein Haken fehlt (bis 0.5.2) |
| Haken-Wert über `st.session_state[key]` setzen, Checkbox ohne `value=` | Nur so übernimmt der Browser einen Wert, der nicht durch Klick entsteht (Sammelaktion) | `value=` aus der Auswahl ableiten |
| Nach jeder Änderung, die nicht durch Klick auf genau diese Checkbox entsteht (Sammelaktion, Rückgängig, gleiche Angabe auf anderen Seiten), die übrigen Checkbox-Schlüssel löschen (`haken_zuruecksetzen`) | Die Übernahme der Haken vor dem Zeichnen (Abschnitt 3) überschriebe sonst die neue Auswahl mit dem alten Haken | Übernahme der Haken entfernen |

Projektvorgaben des Nutzers:
- Ausschließlich lokale Verarbeitung, keine Cloud-Dienste, keine Telemetrie. Einzige Ausnahme (vom Nutzer gewählt am 2026-11-11): Die Mac-App fragt beim Start die neueste Versionsnummer bei GitHub ab, installiert nur nach Rückfrage, abschaltbar.
- Oberfläche, Code-Kommentare und Bezeichner auf Deutsch.
- Zielhardware: Apple Silicon (MacBook Air M2, 8 GB); stand ursprünglich in `design.md` (entfernt, rekonstruiert).
- Nur erfundene Testdaten (z. B. „Erika Mustermann, Musterstadt“).
- Lizenz MIT.

Umgebung und Deployment:
- Laufzeit: Python 3.11 in `venv/` (vom Installer angelegt; auf diesem Mac geprüft 2026-11-13). `.venv/` ist veraltet (siehe „Ungeprüft“).
- Erforderliche Umgebungsvariablen: keine.
- Zielsystem: lokal unter `http://localhost:8501`; Mac-App-Daten in `~/Library/Application Support/Grauzone PRO`.
- Lokale Nutzerdaten, nicht im Repository: `knowledge_base.json`, `vornamen.txt`, `trainingsdaten/`.

Starten und Testen:
- Einrichtung: `Grauzone installieren.command` doppelklicken, oder `python setup_project.py` in einer Python-3.11-Umgebung.
- Start: `./venv/bin/python -m streamlit run app.py` (entspricht `START_GRAUZONE.command`).
- DMG bauen: `sh macos/build_dmg.sh` (Ergebnis in `dist/`).
- Tests: `./venv/bin/python -m unittest discover -s tests`, mit Scan-Test zusätzlich `GRAUZONE_OCR_TEST=1` (etwa 30 s). Vor jedem Commit ausführen. Weiteres Testvorgehen siehe UEBERGABE.md, Abschnitt 5.

## 2. Die drei wichtigsten Learnings

### L1: spaCy-Modelle nicht über `spacy download` installieren
- Problem: Modell-Download unter spaCy 3.5 scheitert mit Fehler 404; die App fand kein Modell.
- Ursache: Der Kompatibilitätslink von `spacy download` liefert für 3.5 keine Version mehr.
- Lösung: Wheels direkt von `https://github.com/explosion/spacy-models/releases/download/<modell>-3.5.0/<modell>-3.5.0-py3-none-any.whl` installieren (Fundstelle: `setup_project.py`, `macos/grauzone-start.sh`, Commit dfe42a9). `load_nlp` in `app.py` lädt nur noch, ohne Download.
- Merksatz: Modellversion und spaCy-Version gemeinsam pinnen; Modelle nur über feste URL installieren.

### L2: Versionskette spaCy 3.5 / numpy 1.x / Python bis 3.11
- Problem: spaCy 3.5 läuft nicht mit numpy 2 oder Python 3.12+.
- Ursache: spaCy 3.5 ist gegen numpy 1.x gebaut.
- Lösung: `requirements.txt:7-8` (`spacy>=3.5.0,<3.6.0`, `numpy<2`), Python-Prüfung in `setup_project.py`, Installer legt Python 3.11 per uv an.
- Merksatz: Keine dieser drei Grenzen einzeln anheben; ein Upgrade betrifft immer alle drei und die Modell-URLs.

### L3: Streamlit muss ausdrücklich lokal und headless laufen
- Problem: Beim ersten Start wartet Streamlit im Terminal auf eine E-Mail-Eingabe; ohne Adressbindung ist die App im Netzwerk erreichbar und fragt die öffentliche IP ab.
- Ursache: Streamlit-Standardeinstellungen.
- Lösung: `.streamlit/config.toml` mit `headless = true`, `address = "localhost"`, `gatherUsageStats = false`; die Mac-App kopiert die Datei als `streamlit-config.toml` mit (Commits dfe42a9, 56b6f82). Browser öffnen die Startskripte erst, wenn `/_stcore/health` antwortet.
- Merksatz: Jede neue Startvariante muss diese Konfiguration mitnehmen.

## 3. Behobene Fehler und Sackgassen: nicht wiederholen

| Symptom | Ursache | Fix (Datei/Commit) | Nicht tun |
|---|---|---|---|
| Ganze Zeilen geschwärzt, Anrede und Kontext weg | Schwärzung auf OCR-Zeilenebene | Wortebene in `erkennung.py` (b222dc7) | Zu zeilenweisen Rechtecken zurückkehren |
| Datum als Telefonnummer erkannt | TEL-Muster zu weit | `_ist_datum` und Mindestziffern in `finde` (`erkennung.py:170`) | Prüfung beim Ändern des TEL-Musters entfernen |
| Absender und Anschrift als eine Fundstelle | spaCy-Entitäten über Zeilenumbrüche | Aufteilen an `\n` (`erkennung.py:162`) | Entitäten ungeteilt übernehmen |
| Buchstabenreste neben Balken bei Scans | OCR-Wortgrenzen ungenau | Zusätzlicher Rand für OCR-Wörter, `width_ths=0.05` (`erkennung.py:71`, `:238`) | Rand für OCR-Wörter auf Textebenen-Niveau senken |
| Auswahl auf anderer Seite verloren | Streamlit löscht Zustand verborgener Widgets | `st.session_state.auswahl` (`app.py:239`) | Auswahl nur über Checkbox-Keys halten |
| Haken entfernt, aber Vorschau, Zähler und Karte blieben rot (0.5.0) | Rechte Spalte (Liste) läuft nach der Vorschau; Auswahl kam zu spät in `st.session_state.auswahl` | Haken vor dem Zeichnen aus den Checkbox-Keys übernehmen (`haken_key`, `app.py`), Export verwerfen; Test `test_haken_entfernen_wirkt_sofort` | Auswahl erst beim Zeichnen der Liste übernehmen, wenn die Liste nach der Vorschau steht |
| Nach „Alle freigeben“ blieb der Haken im Browser gesetzt, Karte und Vorschau waren schon grau (Browserprüfung Paket A, 2026-11-12) | Checkbox mit festem `key` behält im Browser ihren Wert, auch wenn `value=` sich ändert oder der Schlüssel gelöscht wird | Wert vor dem Zeichnen in `st.session_state[key]` schreiben, Checkbox ohne `value=` (`app.py`) | Haken-Zustand nur über `value=` setzen; AppTest allein reicht hier nicht, er kennt den Browserzustand nicht |
| Tests schrieben in die echte `knowledge_base.json` | Abwählen lernt „nie schwärzen“, App liest relativ zum Arbeitsordner | `tests/test_app.py` startet in `tempfile.mkdtemp()` | App-Tests im Projektordner laufen lassen |
| ◀ ▶ und Seitenzahl wechselten nur die Fundstellen-Liste, die Vorschau blieb stehen; Scrollbereich höher als das Fenster | Streamlit scrollt nicht selbst; `st.container(height=900)` fest | `zur_seite_scrollen` und CSS-Höhe in `app.py` (0.4.5) | Feste Container-Höhe über Fensterhöhe; CSS nur auf den Container statt auf seinen Wrapper (`flex: 0 0 800px` gewinnt) |
| Fundstellenliste (rechte Spalte) erscheint nach dem Scannen mehrseitiger PDFs erst deutlich verzögert (Nutzer, 0.5.0) | Streamlit zeigt Elemente in Skriptreihenfolge; die Vorschau mit allen Seiten (Overlay und PNG je Seite) lief vor der rechten Spalte. Messung mit 30 Scan-Seiten (Bildrauschen, Textebene): Liste nach 6,0 s, erst zusammen mit den Seitenbildern | Rechte Spalte steht im Skript vor der Mittelspalte (`app.py`, 0.5.1); danach Liste nach 2,9 s, Seitenbilder nach 7,4 s | Rechte Spalte wieder hinter die Vorschau setzen |
| Quarantäne-Attribut auf kopierten Dateien der Mac-App | Kopieren aus dem App-Bundle | Kopieren per `cat` in `macos/Grauzone-launcher.sh` | `cp` für diese Kopie verwenden |
| Name in XMP-Metadaten, Lesezeichen oder eingebetteter Datei nach Export weiter im PDF (Messung 2026-11-12 mit erfundenen Daten) | `set_metadata({})` leert nur das Info-Wörterbuch; `apply_redactions()` erfasst nur Seiteninhalt | `E.bereinige_pdf` (XMP, Lesezeichen, Anhänge) und `E.pruefe_export` (Text und Helligkeit unter den Balken, Metadaten, Anmerkungen, Formularfelder), Tests `tests/test_export_pruefung.py` (0.4.7) | Beim Export nur `set_metadata({})` aufrufen; Satzzeichen neben einem Fund als Fehler der Prüfung zählen (bleiben absichtlich stehen) |
| Name in PDF-Formularfeld nach Export lesbar über grauem Balken, Wert weiter in der Datei | `apply_redactions()` entfernt keine Formularfelder und Anmerkungen | `oeffne_pdf()` mit `widget.update()` und `doc.bake()` (`app.py`, 0.3.1; jetzt `erkennung.py`, Test `test_formularwert_wird_entfernt`) | PDF in `app.py` direkt mit `pymupdf.open` öffnen |
| Schalter in der Seitenleiste sprang nach dem Einschalten zurück | `st.toggle` mit wechselndem `value=` erzeugt bei jedem Lauf ein neues Widget | Fester `key="update_pruefen"`, Startwert einmal in `st.session_state` (`app.py`, 0.4.0) | Bei Widgets mit gespeichertem Zustand `value=` aus einer Datei ableiten |
| Nach Update der Mac-App lief weiter der alte Code, Export erneut ungeschwärzt | Starter holte nur den Browser nach vorn, wenn schon ein Server lief | Versionsvergleich und Beenden des alten Servers in `macos/Grauzone-launcher.sh`, Version in der Seitenleiste (`app.py` `lies_version`, 0.3.2) | Bei laufendem Server ohne Versionsvergleich nur den Browser öffnen |
| `de-core-news-sm` in `requirements.txt` nicht installierbar | Modell ist kein PyPI-Paket | Aus `requirements.txt` entfernt (c47888b) | Modelle in `requirements.txt` eintragen |

Verworfene Ansätze:
| Ansatz | Warum gescheitert |
|---|---|
| `spacy.cli.download` zur Laufzeit in `load_nlp` (344b23c) | Fehler 404 unter spaCy 3.5, Netzwerkzugriff zur Laufzeit widerspricht dem Lokalprinzip |
| DMG im Repository unter `download/` (56b6f82) | Binärdatei im Verlauf; ersetzt durch Release-Anhang (a29a826) |
| PyInstaller-Bundle (`run_app.py`, `hooks/`, am 2026-11-12 entfernt) | Nicht getestet; würde PyMuPDF (AGPL) mitliefern (rekonstruiert aus UEBERGABE.md) |

## 4. Offene Aufgaben

- [ ] Selbst-Update auf einem Mac mit installierter App prüfen, nach Veröffentlichung von 0.6.0 von 0.5.2 auf 0.6.0 (Priorität hoch). Aufräumen: auf dem zweiten Mac `git branch -d redesign`; `.venv/` löschen. Erledigt: Branch `redesign` (2026-11-12) und `claude/laughing-lamport-dda70o` (2026-11-13, war vollständig in `main` enthalten) auf GitHub gelöscht.
- [ ] Zurückgestellt (vom Nutzer am 2026-11-12, erst angehen, wenn die Grenze `<1.68` angehoben wird): `st.components.v1.html` (Scroll-Sprung in `zur_seite_scrollen`, auch in 0.4.5) ist ab Streamlit 1.68 abgekündigt, Ersatz `st.iframe`; vor Anheben der Grenze umstellen und Sprung im Browser prüfen
- [ ] Datumsprüfung `_ist_datum` in `finde` ist beim jetzigen TEL-Muster wirkungslos (kein Datum passt auf das Muster); bei Änderungen am TEL-Muster Test `test_datum_ist_keine_telefonnummer` beachten (niedrig)
- [x] Behoben 2026-11-12 (für 0.5.2): EasyOCR in `requirements.txt` auf `>=1.7.2,<1.8` begrenzt; alle Tests mit `GRAUZONE_OCR_TEST=1` bestanden. PyTorch (von EasyOCR mitgezogen) bleibt unbegrenzt
- [x] Behoben 2026-11-12 (für 0.5.2, noch nicht veröffentlicht): Dateiname des Exports übernahm den Originalnamen (`Anonymisiert_<Name>`), der selbst Personennamen enthalten kann. Jetzt (Schema vom Nutzer festgelegt) `<JJJJ-MM-TT>_<HH-MM>_Anonymisiert.pdf`/`.md` und `<…>_Pruefprotokoll.md` mit demselben Zeitstempel; Bindestrich statt Doppelpunkt in der Uhrzeit, weil Windows „:“ verbietet und Browser es ersetzen; Protokoll bleibt Markdown; einmal beim Export festgelegt und in `st.session_state.export[6]` gespeichert (`app.py`); Test `test_dateinamen_ohne_originalnamen`
- [ ] Gleiche Person in anderer Schreibweise („Mustermann, Erika“ / „Erika Mustermann“) bekommt im Markdown verschiedene Nummern (niedrig)
- [ ] „Musterweg 12“ bekommt die Art Person, wenn das Sprachmodell (sm) die Straße als Person meldet: `rang` in `finde` stellt PER vor ADR. Geschwärzt wird trotzdem; nur Art und Filter stimmen nicht (niedrig)
- [x] Behoben 2026-11-12 (Muster `PER_UMBRUCH`, Stoppwortliste `NICHT_NAME`, Folgewort nach Anrede am Zeilenumbruch; zusätzlich Muster `PER_FELD` für „Absender:“, „Name:“ u. ä. mit Name, damit auch `lg` „Max Beispiel“ ohne Anrede erfasst): Fund aus Testlauf 2026-11-12 (erfundene Daten, `erkennung.py` ohne Oberfläche, spaCy 3.5.0, PyMuPDF 2.1, EasyOCR 1.7.2 auf CPU; Skript nur im Scratch-Bereich): Name über Zeilenumbruch wird nicht vollständig geschwärzt (Priorität hoch). Bei „Herrn Max⏎Beispiel“ greift das Anrede-Muster nicht (`[ \t]+` quert keinen Umbruch), und die Aufteilung der spaCy-Entitäten an `\n` (`erkennung.py:162`) lässt „Beispiel“ allein ohne Entität zurück. Ergebnis `de_core_news_sm`: „Beispiel“ bleibt lesbar. Ergebnis `de_core_news_lg`: „Max Beispiel“ im Absenderblock wird gar nicht erkannt, „Beispiel“ bleibt zweimal lesbar. Änderung betrifft die Festlegung „Aufteilen an `\n`“ (Abschnitt 3) und braucht vorher Rückfrage.
- [x] Behoben 2026-11-12 (IBAN-Muster mit O/o, I/l-Toleranz und Prüfung `_ist_iban`; Wort mit „@“ wird ganz erfasst, fehlende Punkt-Endung angehängt; Wiederholung des Testlaufs mit `sm` und `lg` ohne Rest): Fund aus Testlauf 2026-11-12: Auf Scan-Seiten werden E-Mail und IBAN wegen OCR-Fehlern nicht erkannt (Priorität hoch). Beispiel OCR-Text: „erika.mustermann@example org“ (Punkt fehlt) und „DEO2 1203 000o 000o 2020 51“ (O statt 0); die Muster `MAIL` und `IBAN` greifen dann nicht, beide Angaben bleiben im Bild stehen. Textebene derselben Seite wird korrekt erkannt. Lösungsansatz offen (fehlertolerante Muster, Warnhinweis bei Scan-Seiten, Prüfung auf „@“ im Seitentext).
- [ ] Fund aus Testlauf 2026-11-12 (niedrig): Mit `de_core_news_lg` wird „Stadt“ aus „Stadt Musterstadt“ als ORT erkannt, „Musterstadt“ im selben Satz auf Seite 1 nicht; mit `sm` umgekehrt. Verhalten hängt vom Modell ab. Bei Scans sitzt der Balken vor „Mustermann“ nach „Frau“ minimal zu weit links und kürzt das „u“ von „Frau“ an (kosmetisch).
- [ ] Mehrseitige echte Dokumente testen, Text- und Scan-Seiten gemischt, auch Formulare; dabei Tempo der Vorschau bei vielen Seiten prüfen (Priorität hoch, nächster Schritt). Vorschlag: gemischtes Test-PDF mit erfundenen Daten (Textseiten, Scan-Seite, Formularfeld, Name über Zeilenumbruch) durch `erkennung.py` laufen lassen und Export prüfen. Im selben Zug (vom Nutzer am 2026-11-12 so festgelegt): breitere Balken bei Scans (Wortgrenzen genauer schätzen, ohne Buchstabenreste) sowie Windows und Gatekeeper-Dialog nach echtem Download
- [x] Umgesetzt 2026-11-12 in Paket C (0.6.0): Gesundheitsdaten (Art. 9 DSGVO), Geburtsdatum nur mit Kontext, Kennnummern. Offen bleibt: Wortliste `GES_WOERTER` an echten Dokumenten erweitern; „BIC“ prüft kein Länderkürzel (niedrig)
- [ ] OCR-Dauer von etwa 15 bis 20 s pro Scan-Seite auf der CPU (niedrig)
- [ ] Notarisierung, erfordert Apple-Entwicklerkonto (niedrig)

### Nächster konkreter Schritt

Stand 2026-11-13: 0.6.0 (Pakete A, B, C) veröffentlicht: Tag `v0.6.0` auf 33b83b5, Release mit allen vier Anhängen als neuestes markiert, Prüfsumme der heruntergeladenen Dateien stimmt, `releases/latest/download/VERSION` liefert 0.6.0 (davon hängt das Selbst-Update ab). Gesamtprüfung 2026-11-13 mit gemischtem Test-PDF (Textseite, Scan per OCR, Formularfeld; erfundene Daten, `de_core_news_lg`): alle Angaben auf Text- und Scan-Seite erkannt und entfernt, Exportprüfung bestanden, Aktenzeichen und Briefdatum bleiben lesbar; 30 Seiten Regeln in 0,3 s.

Als Nächstes, in dieser Reihenfolge:
1. Nutzer am Mac: Selbst-Update von 0.5.2 auf 0.6.0 durchlaufen (seit 0.4.0 nie an einer installierten App geprüft, größtes Risiko).
2. Nutzer: zwei, drei echte Dokumente (Brief, Scan, Formular) bearbeiten und notieren, was übersehen oder zu viel geschwärzt wurde, ohne Inhalte weiterzugeben.
3. Paket D „Bereich von Hand schwärzen“ (Unterschrift, Foto, Stempel, Handschrift; heute nicht schwärzbar): Rechteck in der Vorschau aufziehen. Streamlit wertet keine Klicks auf Bilder aus; Zusatzpaket oder Koordinatenfelder vorher mit dem Nutzer abstimmen.
4. Je nach Ergebnis von 2: Wortliste `GES_WOERTER` erweitern; Feldnamen von Formularen vor `doc.bake()` als Kontext nutzen (heute steht ein Name im Feld „Name“ nur unter „zu prüfen“); BIC-Länderkürzel; „Musterweg 12“ als Anschrift.
5. Später, mit Vorab-Entscheidung des Nutzers: Sitzungen speichern (Datenschutz der Sitzungsdatei), Tastaturkürzel (nach Umstellung auf `st.iframe`), wiederkehrende Passagen (Briefkopf, Fußzeile).

Hinweis aus der Gesamtprüfung (zur Kenntnis, keine Änderung ohne Auftrag): „nie schwärzen“ gilt global (Festlegung des Nutzers); seit Paket C betrifft das auch von Hand freigegebene Gesundheitsangaben und Kennnummern.

Prüfen vor jedem Commit: `./venv/bin/python -m unittest discover -s tests`.

## Ungeprüft

- `.venv/` (Python 3.9.6, spaCy 3.5.4, numpy 2.0.2) widerspricht `requirements.txt` und wird nicht gebraucht; `.venv/` steht in `.gitignore` und kann vom Nutzer gelöscht werden. `venv/` ist seit 2026-11-12 passend eingerichtet (geprüft 2026-11-13: Python 3.11.18, spaCy 3.5.4, numpy 1.26.4, Streamlit 1.67.0, PyMuPDF 2.1).
- Herkunft und Zweck von `trainingsdaten/` und `dist/run_app.app` (vom 11.05.2026) sind nicht geklärt.
