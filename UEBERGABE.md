# Übergabe: Grauzone PRO

Stand: 11.11.2026, Version **0.3.0** (Tag `v0.3.0`, Release mit DMG veröffentlicht)

Dieses Dokument fasst zusammen, wie das Projekt aufgebaut ist, wie man eine neue Version herausbringt und was noch offen ist. Für Nutzerinnen und Nutzer ist die [README](README.md) gedacht.

---

## 1. Worum es geht

Grauzone PRO schwärzt personenbezogene Daten in PDF-Dokumenten, vollständig lokal. Oberfläche: Streamlit im Browser unter `http://localhost:8501`, nur auf dem eigenen Rechner erreichbar.

| Baustein | Aufgabe |
|---|---|
| PyMuPDF (`fitz`) | PDF lesen, Wortpositionen aus der Textebene, Schwärzen (`apply_redactions`) |
| EasyOCR | Texterkennung für gescannte Seiten (wortweise, `width_ths=0.05`) |
| spaCy 3.5 + `de_core_news_lg`/`_sm` | Personen, Orte, Organisationen |
| Streamlit | Oberfläche |

## 2. Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Oberfläche: Hochladen, Scannen (Seite / alle Seiten), Fundstellen-Liste, Lernen, Export |
| `erkennung.py` | Erkennung ohne Streamlit: Wörter holen, Seitentext bauen, Fundstellen suchen, Rechtecke berechnen |
| `requirements.txt` | Bibliotheken; **spaCy < 3.6 und numpy < 2 sind Pflicht** |
| `.streamlit/config.toml` | nur `localhost`, keine Nutzungsstatistik, `headless` (keine E-Mail-Abfrage) |
| `Grauzone installieren.command` | Einrichtung aus dem Quellcode per Doppelklick (uv + Python 3.11) |
| `START_GRAUZONE.command`, `starten.command` | Start nach der Einrichtung |
| `setup_project.py` | Einrichtung für den Weg über das Terminal |
| `macos/` | Mac-App: Starter, Einrichtungsskript, Icon, `build_dmg.sh`, `VERSION` |
| `run_app.py`, `hooks/` | PyInstaller-Weg (nicht genutzt, nicht getestet) |
| `evaluate_system.py`, `generate_train_data.py`, `design.md` | aus der ersten Fassung, nicht überarbeitet |

Lokale Daten (nicht im Repository): `knowledge_base.json` (gelernte Begriffe: `blacklist` = immer schwärzen, `whitelist` = nie schwärzen), `vornamen.txt`.

## 3. Wie die Mac-App funktioniert

Die DMG (~470 KB) enthält nur einen Starter, keine Bibliotheken.

1. `Grauzone PRO.app/Contents/MacOS/Grauzone` (= `macos/Grauzone-launcher.sh`) kopiert `app.py`, `erkennung.py`, `requirements.txt`, `VERSION` und die Streamlit-Einstellungen nach `~/Library/Application Support/Grauzone PRO` (per `cat`, damit kein Quarantäne-Attribut mitkommt) und öffnet dort `Grauzone starten.command` im Terminal.
2. `Grauzone starten.command` (= `macos/grauzone-start.sh`) richtet beim ersten Start oder nach einer Änderung an `VERSION`/`requirements.txt` alles ein: uv, Python 3.11, Bibliotheken, spaCy-Modelle, EasyOCR-Modelle (~2 GB). Merker: Datei `.eingerichtet` mit Prüfsumme.
3. Danach startet Streamlit; ein Hintergrundprozess öffnet den Browser, sobald `/_stcore/health` antwortet. Terminalfenster schließen = Grauzone beenden.

Die App ist nur ad hoc signiert, nicht notarisiert. macOS fragt beim ersten Öffnen nach (Rechtsklick → Öffnen bzw. „Dennoch öffnen“).

## 4. Neue Version herausbringen

1. Änderungen machen und testen (siehe Abschnitt 5).
2. Versionsnummer in `macos/VERSION` erhöhen. Dadurch prüft die App beim nächsten Start ihre Einrichtung neu.
3. Neue Dateien, die die App braucht, in `macos/Grauzone-launcher.sh` (Kopierschleife) **und** `macos/build_dmg.sh` (`cp … Resources/grauzone/`) eintragen.
4. `sh macos/build_dmg.sh` → `dist/Grauzone-PRO-<Version>.dmg` (der Ordner `dist/` wird nicht eingecheckt).
5. Commit, Tag `v<Version>` setzen, beides pushen.
6. Auf GitHub unter *Releases → Draft a new release* das Tag wählen und die DMG anhängen. Die README verlinkt immer auf `releases/latest`.

## 5. Testen

- **Erkennung ohne Oberfläche:** `erkennung.py` lässt sich direkt mit PyMuPDF, spaCy und EasyOCR aufrufen (`woerter_aus_textebene` / `woerter_aus_ocr` → `seitentext` → `finde` → `wort_rechteck`). Danach `apply_redactions()` und mit `page.get_text()` prüfen, dass an den geschwärzten Stellen kein Text mehr steht.
- **Scan-Fall:** Testseite als Bild in ein neues PDF einfügen (ohne Textebene) und das Ergebnis als Bild ansehen: Es dürfen keine Buchstabenreste neben den Balken stehen.
- **App:** Datenordner mit einem eigenen `HOME` testen, damit der echte `~/Library/Application Support/Grauzone PRO` unberührt bleibt.
- Nur erfundene Testdaten verwenden (z. B. „Erika Mustermann, Musterstadt“).

## 6. Bekannte Fallstricke

- `python -m spacy download …` funktioniert mit spaCy 3.5 nicht mehr (Link mit Fehler 404). Modelle direkt als Wheel installieren: `https://github.com/explosion/spacy-models/releases/download/<modell>-3.5.0/<modell>-3.5.0-py3-none-any.whl`.
- spaCy 3.5 läuft nur mit Python bis 3.11 und nur mit numpy 1.x.
- Ohne `headless = true` wartet Streamlit beim allerersten Start im Terminal auf eine E-Mail-Eingabe.
- Ohne `address = "localhost"` ist Streamlit im ganzen Netzwerk erreichbar und fragt die öffentliche IP-Adresse ab.
- Streamlit löscht den Zustand von Widgets, die gerade nicht angezeigt werden. Die Auswahl je Seite liegt deshalb in `st.session_state.auswahl`, nicht nur in den Checkboxen.

## 7. Offene Punkte

- **Bei Scans etwas breitere Balken:** EasyOCR kennt Wortgrenzen nur ungefähr. Anteilig geschätzte Wortteile bekommen viel Rand, dabei verschwindet manchmal ein Buchstabe des Nachbarworts.
- **Mehrseitige echte Dokumente** sind noch nicht getestet, ebenso **Windows** und der Gatekeeper-Dialog nach einem echten Download.
- **Gelernte „nie schwärzen“-Begriffe** gelten überall. Ein versehentlich abgewähltes Wort (z. B. ein Nachname) wird danach in allen Dokumenten übersehen, bis man es wieder anhakt oder das Gedächtnis löscht.
- **Lange Dokumente:** Die Texterkennung dauert etwa 15 bis 20 Sekunden pro Scan-Seite auf der CPU.
- **Notarisierung** bräuchte ein Apple-Entwicklerkonto (99 €/Jahr).
- **Alte Dateien** (`evaluate_system.py`, `generate_train_data.py`, `design.md`, PyInstaller-Weg) sind nicht an 0.3.0 angepasst.
- **Lizenz:** Grauzone steht unter MIT. PyMuPDF steht unter AGPL. Solange die Bibliotheken bei der Einrichtung geladen und nicht mitgeliefert werden, ist das unproblematisch; beim PyInstaller-Weg nicht.

## 8. Verlauf

| Version | Datum | Inhalt |
|---|---|---|
| 0.1.0 / 0.1.1 | 18.05.2026 | erste Fassung, Schwärzung ganzer OCR-Zeilen |
| 0.2.0 | 11.11.2026 | Installation per Doppelklick, Mac-App als DMG mit Icon, MIT-Lizenz, Streamlit nur lokal, Modell-Download repariert |
| 0.3.0 | 11.11.2026 | Schwärzung auf Wortebene, mehr Muster, alle Seiten, Begriffe ergänzen, Metadaten entfernen |
