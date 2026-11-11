# Projektstand: Grauzone PRO

Stand: 2026-11-11, Branch main, Commit 4a23fa8 (Release `v0.4.2`), darauf folgt der Commit zu 0.4.3 (`macos/VERSION` = 0.4.3)

Ergänzt [UEBERGABE.md](UEBERGABE.md). Dort stehen Dateiübersicht, Funktionsweise der Mac-App, Release-Ablauf (Abschnitt 4) und Testanleitung (Abschnitt 5). Diese Datei hält Festlegungen, Learnings und Sackgassen fest und wird nicht mit UEBERGABE.md zusammengeführt.

## Verbindlichkeit

Abschnitt 1 (Festlegungen) und Abschnitt 3 beschreiben abgestimmte und getestete Lösungen. Sie werden nicht geändert, zurückgebaut oder umgebaut, solange keine neue Anforderung das verlangt. Verlangt eine neue Funktion eine Änderung, vor der Umsetzung die betroffene Festlegung benennen, die Änderung begründen und Rückfrage halten.

## 1. Kernarchitektur und Tech-Stack

Zweck: Personenbezogene Daten in PDF-Dokumenten vollständig lokal erkennen und physisch schwärzen.

Stack: Python 3.11 (Mac-App/Installer über uv), Streamlit, PyMuPDF (`import pymupdf`), EasyOCR, spaCy `>=3.5.0,<3.6.0` mit `de_core_news_lg` (Ersatz `de_core_news_sm`, je 3.5.0), `numpy<2`, Pillow, Faker. Streamlit `>=1.50,<1.68` (getestet: 1.67.0; `width=` geprüft ab 1.50). PyMuPDF `>=2.1,<2.2` ab Python 3.11, sonst `>=1.26.5,<1.27` (beide getestet). EasyOCR ist nicht begrenzt (installiert: 1.7.2).

Struktur:
- `app.py`: Streamlit-Oberfläche: Hochladen, Scannen (`scanne`, Seite oder alle Seiten), Fundstellenliste, Lernen über `knowledge_base.json`, Export mit `apply_redactions()` und `set_metadata({})`.
- `erkennung.py`: Erkennung ohne Streamlit: `woerter_aus_textebene`, `woerter_aus_ocr`, `seitentext`, `finde`, `wort_rechteck`, `markdown` (Export); Datenklassen `Wort`, `Fund`.
- `.streamlit/config.toml`: `address = "localhost"`, `headless = true`, `gatherUsageStats = false`.
- `macos/`: `Grauzone-launcher.sh` (App-Starter), `grauzone-start.sh` (Einrichtung und Start im Datenordner), `grauzone-update.sh` (Selbst-Update), `build_dmg.sh`, `make_icon.py`, `VERSION`.
- `Grauzone installieren.command`, `START_GRAUZONE.command`, `starten.command`, `setup_project.py`: Einrichtung und Start aus dem Quellcode.
- Nicht an 0.3.0 angepasst: `run_app.py`, `hooks/`, `evaluate_system.py`, `generate_train_data.py`, `design.md`.

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
| PDF immer über `oeffne_pdf()` öffnen (Formularfelder und Anmerkungen per `doc.bake()` in die Seite) | Nur so entfernt `apply_redactions()` auch deren Text; Scan und Export sehen denselben Inhalt | Formularfelder unverändert lassen; Felder nur löschen (verliert nicht betroffene Werte) |

Projektvorgaben des Nutzers:
- Ausschließlich lokale Verarbeitung, keine Cloud-Dienste, keine Telemetrie. Einzige Ausnahme (vom Nutzer gewählt am 2026-11-11): Die Mac-App fragt beim Start die neueste Versionsnummer bei GitHub ab, installiert nur nach Rückfrage, abschaltbar.
- Oberfläche, Code-Kommentare und Bezeichner auf Deutsch.
- Zielhardware laut `design.md`: Apple Silicon (MacBook Air M2, 8 GB) (rekonstruiert).
- Nur erfundene Testdaten (z. B. „Erika Mustermann, Musterstadt“).
- Lizenz MIT.

Umgebung und Deployment:
- Laufzeit: Python 3.11 in `venv/` (vom Installer angelegt). Die lokal vorhandenen `venv/` und `.venv/` haben Python 3.9.6 und `numpy 2.0.2`, passen also nicht zu `requirements.txt` (siehe „Ungeprüft“).
- Erforderliche Umgebungsvariablen: keine.
- Zielsystem: lokal unter `http://localhost:8501`; Mac-App-Daten in `~/Library/Application Support/Grauzone PRO`.
- Lokale Nutzerdaten, nicht im Repository: `knowledge_base.json`, `vornamen.txt`, `trainingsdaten/`.

Starten und Testen:
- Einrichtung: `Grauzone installieren.command` doppelklicken, oder `python setup_project.py` in einer Python-3.11-Umgebung.
- Start: `./venv/bin/python -m streamlit run app.py` (entspricht `START_GRAUZONE.command`).
- DMG bauen: `sh macos/build_dmg.sh` (Ergebnis in `dist/`).
- Automatisierte Tests gibt es nicht; Testvorgehen siehe UEBERGABE.md, Abschnitt 5.

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
| Quarantäne-Attribut auf kopierten Dateien der Mac-App | Kopieren aus dem App-Bundle | Kopieren per `cat` in `macos/Grauzone-launcher.sh` | `cp` für diese Kopie verwenden |
| Name in PDF-Formularfeld nach Export lesbar über grauem Balken, Wert weiter in der Datei | `apply_redactions()` entfernt keine Formularfelder und Anmerkungen | `oeffne_pdf()` mit `widget.update()` und `doc.bake()` (`app.py`, 0.3.1) | PDF in `app.py` direkt mit `pymupdf.open` öffnen |
| Schalter in der Seitenleiste sprang nach dem Einschalten zurück | `st.toggle` mit wechselndem `value=` erzeugt bei jedem Lauf ein neues Widget | Fester `key="update_pruefen"`, Startwert einmal in `st.session_state` (`app.py`, 0.4.0) | Bei Widgets mit gespeichertem Zustand `value=` aus einer Datei ableiten |
| Nach Update der Mac-App lief weiter der alte Code, Export erneut ungeschwärzt | Starter holte nur den Browser nach vorn, wenn schon ein Server lief | Versionsvergleich und Beenden des alten Servers in `macos/Grauzone-launcher.sh`, Version in der Seitenleiste (`app.py` `lies_version`, 0.3.2) | Bei laufendem Server ohne Versionsvergleich nur den Browser öffnen |
| `de-core-news-sm` in `requirements.txt` nicht installierbar | Modell ist kein PyPI-Paket | Aus `requirements.txt` entfernt (c47888b) | Modelle in `requirements.txt` eintragen |

Verworfene Ansätze:
| Ansatz | Warum gescheitert |
|---|---|
| `spacy.cli.download` zur Laufzeit in `load_nlp` (344b23c) | Fehler 404 unter spaCy 3.5, Netzwerkzugriff zur Laufzeit widerspricht dem Lokalprinzip |
| DMG im Repository unter `download/` (56b6f82) | Binärdatei im Verlauf; ersetzt durch Release-Anhang (a29a826) |
| PyInstaller-Bundle (`run_app.py`, `hooks/`) | Nicht getestet; würde PyMuPDF (AGPL) mitliefern (rekonstruiert aus UEBERGABE.md) |

## 4. Offene Aufgaben

- [ ] Nächste Version (Ideen des Nutzers vom 2026-11-11, Reihenfolge offen):
  - [ ] Oberfläche modern gestalten (UI/UX)
- [ ] Release 0.4.3 mit allen vier Anhängen veröffentlichen (Priorität hoch); Selbst-Update von 0.4.0 auf 0.4.1 beim Nutzer echt prüfen
- [ ] EasyOCR ist nicht nach oben begrenzt (installiert 1.7.2) (niedrig)
- [ ] Dateiname des Exports übernimmt den Originalnamen (`Anonymisiert_<Name>`), der selbst Personennamen enthalten kann (mittel)
- [ ] Gleiche Person in anderer Schreibweise („Mustermann, Erika“ / „Erika Mustermann“) bekommt im Markdown verschiedene Nummern (niedrig)
- [ ] Mehrseitige echte Dokumente testen, Text- und Scan-Seiten gemischt, auch Formulare (Priorität hoch, nächster Schritt)
- [ ] Gesundheitsangaben (Art. 9 DSGVO, z. B. „Medikation: 30 mg“), Alter und Datum werden nicht erkannt; Bedarf klären (mittel)
- [ ] Breitere Balken bei Scans: Wortgrenzen genauer schätzen, ohne Buchstabenreste (mittel)
- [ ] Whitelist gilt global; versehentlich abgewählte Nachnamen werden in allen Dokumenten übersehen (mittel)
- [ ] Windows und Gatekeeper-Dialog nach echtem Download testen (mittel)
- [ ] OCR-Dauer von etwa 15 bis 20 s pro Scan-Seite auf der CPU (niedrig)
- [ ] Alte Dateien (`evaluate_system.py`, `generate_train_data.py`, `design.md`, PyInstaller-Weg) anpassen oder entfernen (niedrig)
- [ ] Notarisierung, erfordert Apple-Entwicklerkonto (niedrig)

### Nächster konkreter Schritt

Mehrseitigen Durchlauf mit `erkennung.py` ohne Oberfläche prüfen. Dazu in einer Python-3.11-Umgebung (`./venv/bin/python` nach dem Installer) ein Testskript im Scratch-Bereich anlegen, das mit PyMuPDF ein PDF aus mindestens drei Seiten mit erfundenen Daten erzeugt: Seite 1 mit Textebene, Seite 2 als eingefügtes Bild ohne Textebene, Seite 3 mit Fundstellen über einen Zeilenumbruch. Je Seite den Ablauf aus `app.py` `scanne` nachbilden (`woerter_aus_textebene`, bei weniger als drei Wörtern `woerter_aus_ocr`, dann `seitentext`, `finde`, `wort_rechteck`), Redaktionen anlegen, `apply_redactions()` aufrufen und speichern. Erwartet: Mit `page.get_text()` steht an keiner geschwärzten Stelle mehr Text; auf der Scan-Seite zeigt das gerenderte Bild keine Buchstabenreste; nicht betroffene Wörter bleiben erhalten. Anschließend denselben Ablauf in der App mit „Alle Seiten“ und Export prüfen und Abweichungen in Abschnitt 3 oder 4 eintragen.

## Ungeprüft

- Die lokalen Umgebungen `venv/` (Python 3.9.6, spaCy 3.8.2, numpy 2.0.2, Modelle 3.8.0) und `.venv/` (Python 3.9.6, spaCy 3.5.4, numpy 2.0.2) widersprechen `requirements.txt`. Ob sie noch gebraucht werden, ist offen; `Grauzone installieren.command` würde `venv/` mit Python 3.11 neu anlegen. `.venv/` ist nicht in `.gitignore`.
- Ob die Version 0.3.0 in der laufenden App vollständig getestet wurde, ist nur durch UEBERGABE.md belegt, nicht durch Tests im Repository.
- Herkunft und Zweck von `trainingsdaten/` und `dist/run_app.app` (vom 11.05.2026) sind nicht geklärt.
