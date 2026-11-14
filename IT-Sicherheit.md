# Grauzone PRO: Information für die IT-Sicherheit

Stand: 13.11.2026, Version 0.8.0
Ansprechperson: [Name, Dienststelle, Telefon]

Dieses Dokument beschreibt Grauzone PRO, damit die IT prüfen kann, ob und unter welchen Bedingungen das Programm im Netz der Verwaltung eingesetzt werden darf. Es enthält am Ende eine Liste mit Prüffragen und die Befehle, mit denen sich die Angaben nachprüfen lassen.

## 1. Zweck

Grauzone PRO erkennt personenbezogene Daten in PDF-Dokumenten und schwärzt sie dauerhaft, z. B. vor einer Weitergabe nach IFG oder vor der Herausgabe von Akten. Der Text unter den Balken wird aus der Datei entfernt, nicht nur abgedeckt.

Erkannt werden u. a.:
- Namen
- Anschriften
- Telefonnummern und E-Mail-Adressen
- IBAN
- Geburtsdaten (nur mit Kontext wie „geb.“)
- Kennnummern wie Steuer-ID, Versicherungs- oder Kundennummer
- Gesundheitsangaben

Jede Fundstelle wird angezeigt und muss von der bearbeitenden Person bestätigt oder abgewählt werden. Weitere Stellen können von Hand markiert werden. Das Programm ist ein Hilfsmittel; die Verantwortung für die vollständige Schwärzung bleibt bei der bearbeitenden Person.

## 2. Steckbrief

| Merkmal | Angabe |
|---|---|
| Art | Lokale Web-Anwendung: Python-Server auf dem eigenen Rechner, Bedienung im Browser |
| Plattform | macOS auf Apple Silicon (getestet: MacBook Air M2, 8 GB). Windows: derzeit nicht verfügbar, siehe Abschnitt 11 |
| Programmiersprache | Python 3.11 |
| Umfang des eigenen Codes | etwa 2.200 Zeilen Python (`app.py`, `erkennung.py`) und 4 Shell-Skripte (zusammen etwa 340 Zeilen) |
| Quellcode | öffentlich: https://github.com/dirkblauhut/grauzone_pro |
| Lizenz | MIT (eigener Code); Bibliotheken siehe Abschnitt 7 |
| Admin-Rechte | nicht erforderlich; Installation und Betrieb im Benutzerkonto |
| Cloud-Dienste, KI-Dienste, Telemetrie | keine. Sprach- und Texterkennungsmodelle laufen lokal |
| Netzwerk im Betrieb | nur eine abschaltbare Abfrage der Versionsnummer bei GitHub beim Start (Abschnitt 4.2) |
| Dauerhaft gespeicherte Dokumentdaten | keine; Dokumente werden nur im Arbeitsspeicher verarbeitet (Abschnitt 5) |

## 3. Aufbau und Datenfluss

```
Browser (http://localhost:8501)
    │  Hochladen der PDF, Bedienung, Download der Ergebnisse
    ▼
Streamlit-Server (Python, nur an localhost gebunden)
    │  PDF im Arbeitsspeicher
    ├─ Textebene lesen (PyMuPDF) oder Texterkennung bei Scans (EasyOCR, lokal)
    ├─ Fundstellen suchen: Sprachmodell spaCy (lokal), Regeln, Prüfziffern,
    │  Vornamenliste, gelernte Begriffe
    ├─ Prüfung und Auswahl durch die bearbeitende Person
    └─ Export: physisch schwärzen, Datei bereinigen, Ergebnis prüfen
    ▼
Download über den Browser: geschwärztes PDF, Markdown-Text, Prüfprotokoll
```

- **Server nur lokal:** Er lauscht ausschließlich auf `localhost` (127.0.0.1), Port 8501, und ist aus dem Netz nicht erreichbar. Festgelegt in `.streamlit/config.toml` (`address = "localhost"`).
- **Schutz gegen Cross-Site-Anfragen:** Streamlit hat den XSRF-Schutz eingeschaltet (Standard).
- **Upload-Grenze:** 200 MB je Datei.
- **Nutzungsstatistik:** Die Streamlit-Nutzungsstatistik ist abgeschaltet (`gatherUsageStats = false`).
- **Beenden:** Der Server endet mit der Schaltfläche „Beenden“ oder durch Schließen des Terminalfensters.

### Was beim Export passiert

1. **Freilegen:** Inhalte, die man beim Lesen nicht sieht, werden schon beim Öffnen sichtbar gemacht, damit sie mitgeprüft werden:
   - Text außerhalb des sichtbaren Seitenausschnitts
   - ausgeblendete Ebenen
   - Formularfeldwerte und Anmerkungen, die in die Seite übernommen werden
2. **Schwärzen:** Die markierten Stellen werden physisch entfernt (PyMuPDF `apply_redactions`). Text, Bilder und Vektorgrafik unter dem Balken sind danach nicht mehr in der Datei.
3. **Bereinigen:** Aus der Datei werden zusätzlich entfernt:
   - Metadaten (Info und XMP)
   - Lesezeichen und eingebettete Dateien
   - Verknüpfungen nach außen (z. B. `mailto:`)
   - Seitenbezeichnungen
   - JavaScript und automatische Aktionen
   - Strukturbaum mit Alternativtexten
   - Formular-Reste
   - Vorschaubilder
   - Metadaten einzelner Objekte

   Danach wird die Datei vollständig neu geschrieben, nicht mehr benötigte Objekte werden verworfen (`garbage=4`).
4. **Prüfen:** Die exportierte Datei wird erneut geöffnet. Geprüft wird:
   - ob unter jedem Balken noch Text steht
   - ob jeder Balken schwarz ist
   - ob Metadaten, Anmerkungen, Formularfelder oder verborgene Reste übrig sind

   Das Ergebnis wird angezeigt und im Prüfprotokoll vermerkt.
5. **Prüfprotokoll** (Markdown): Es enthält:
   - SHA-256-Hash des Originals (nicht den Dateinamen)
   - Zahl der Fundstellen je Art (gefunden, geschwärzt, abgewählt)
   - verwendete Version und Sprachmodell
   - Ergebnis der Prüfung

   Die Exportdateien heißen nach Datum und Uhrzeit (z. B. `2026-11-13_14-05_Anonymisiert.pdf`), nicht nach dem Original, weil dessen Name selbst Personennamen enthalten kann.

**Folge der Bereinigung:** Das Ergebnis hat keine Tags für Screenreader mehr (Barrierefreiheit), weil der Strukturbaum Namen in Alternativtexten enthalten kann.

## 4. Netzwerkzugriffe

### 4.1 Einmalig bei der Einrichtung (etwa 2 GB)

Beim ersten Start (und nach einem Update, das die Liste der Bibliotheken ändert) lädt das Startskript alles Nötige aus dem Internet:

| Was | Von | Wofür |
|---|---|---|
| Installationsskript für `uv` | `https://astral.sh/uv/install.sh`, Programm von `github.com` (Release-Dateien des Herstellers Astral) | Paketverwaltung, legt die Python-Umgebung an. Wird nur geladen, wenn `uv` fehlt |
| Python 3.11 | `github.com` (Projekt python-build-standalone, über `uv`) | eigenes Python, das System-Python bleibt unberührt |
| Python-Bibliotheken | `pypi.org`, `files.pythonhosted.org` | Abschnitt 7 |
| Sprachmodelle `de_core_news_sm`, `de_core_news_lg` (Version 3.5.0) | `github.com/explosion/spacy-models/releases/…` | Erkennung von Namen und Orten |
| Texterkennungs-Modelle (`craft_mlt_25k`, `latin_g2`, etwa 94 MB) | `github.com/JaidedAI/EasyOCR/releases/…` | Texterkennung bei Scans |

GitHub liefert Release-Dateien über `objects.githubusercontent.com` bzw. `release-assets.githubusercontent.com` aus. Alle Verbindungen laufen über HTTPS. Ein Proxy wird über die üblichen Umgebungsvariablen (`HTTPS_PROXY`) genutzt.

### 4.2 Im Betrieb

| Zugriff | Wann | Inhalt | Abschalten |
|---|---|---|---|
| `https://github.com/dirkblauhut/grauzone_pro/releases/latest/download/VERSION` | bei jedem Start der Mac-App, Zeitlimit 5 s | Abruf einer Textdatei mit der Versionsnummer. Es werden keine Dokumentdaten, Kennungen oder Nutzungsdaten gesendet; GitHub sieht wie bei jedem Abruf IP-Adresse und Zeitpunkt | Schalter „Beim Start nach neuen Versionen suchen“ (⚙ in der App) oder Datei `.keine-updatepruefung` im Datenordner |
| Update-Paket und Prüfsummen vom selben Release | nur wenn eine neuere Version existiert **und** die Person im Terminal mit „j“ zustimmt | Download | wie oben |
| Texterkennungs-Modelle von GitHub | nur falls die Modelle in `~/.EasyOCR` fehlen (z. B. gelöscht) | Download | Modelle vorhanden lassen; Zugriff sperren |

Sonst baut das Programm keine Verbindung nach außen auf. Ohne Internet startet und arbeitet es normal; die Versionsabfrage schlägt dann still fehl.

## 5. Daten und Speicherorte

**Dokumente:**
- **Verarbeitung:** Das hochgeladene PDF, die Seitenbilder und die Fundstellen liegen nur im Arbeitsspeicher des Servers. Sie werden nicht auf die Festplatte geschrieben, nicht protokolliert und nicht übertragen.
- **Ende der Sitzung:** Mit dem Beenden oder dem Laden eines anderen Dokuments sind sie weg.
- **Ergebnisse:** Die Downloads speichert der Browser, in der Regel unter `Downloads`.
- **Original:** Das Original wird nicht verändert.

**Dateien auf dem Rechner (macOS):**

| Ort | Inhalt | Schutzbedarf |
|---|---|---|
| `~/Library/Application Support/Grauzone PRO/` | Programmdateien, Python-Umgebung `venv/` (etwa 2 GB), Konfiguration | Programmcode, im Benutzerkonto beschreibbar |
| …`/knowledge_base.json` | **gelernte Begriffe im Klartext:** „nie schwärzen“ (z. B. Behördennamen, die fälschlich erkannt wurden) und „immer schwärzen“ (Begriffe, die die Person ausdrücklich für künftige Dokumente vorgemerkt hat, **das können Namen sein**) | personenbezogen möglich; gilt für alle künftigen Dokumente |
| …`/vornamen.txt` | Liste zusätzlicher Vornamen | gering |
| …`/.keine-updatepruefung` | vorhanden = Versionsabfrage aus | – |
| `~/.EasyOCR/` | Texterkennungs-Modelle | – |
| `~/.local/bin/uv`, `~/.local/share/uv/`, `~/.cache/uv/` | Paketverwaltung, Python 3.11, Download-Zwischenspeicher | – |

Die App schreibt keine Protokolldateien. Im Terminalfenster erscheinen nur Start- und Fehlermeldungen des Servers, keine Dokumentinhalte.

## 6. Installation, Rechte und Update

- **Verteilung:** Ein DMG (etwa 500 KB) enthält nur die App „Grauzone PRO“ als Starter mit den Programmdateien. Die Bibliotheken lädt der erste Start (Abschnitt 4.1). PyMuPDF wird deshalb nicht mitgeliefert, sondern beim Nutzer installiert (Lizenzfrage, siehe Abschnitt 7).
- **Rechte:** Alles läuft mit den Rechten der angemeldeten Person. Systemordner, Systemeinstellungen, Autostart, Hintergrunddienste und Kernel-Erweiterungen werden nicht angefasst.
- **Signatur:** Die App ist **nicht** mit einem Apple-Entwicklerzertifikat signiert und **nicht** notarisiert. macOS (Gatekeeper) verlangt beim ersten Öffnen eine manuelle Freigabe.
- **Selbst-Update:**
  - Ablauf: Nach Rückfrage werden Update-Paket und `SHA256SUMS` vom GitHub-Release geladen und die Prüfsumme kontrolliert. Danach werden 7 Dateien im Datenordner ersetzt.
  - Grenze: Die Prüfsumme schützt vor Übertragungsfehlern, aber nicht vor einem manipulierten Release, weil sie aus derselben Quelle kommt. Eine kryptografische Signatur des Pakets gibt es nicht. Die Echtheit hängt damit am GitHub-Konto des Entwicklers.
- **Deinstallation:** App löschen sowie die Ordner aus Abschnitt 5.

## 7. Abhängigkeiten

Installiert aus `requirements.txt` mit Versionsgrenzen nach oben und unten. Es gibt **keine Lockdatei mit festen Versionen und Hashes**: Eine Neuinstallation kann innerhalb der Grenzen neuere Unterversionen laden. Diese Tabelle zeigt den auf dem Entwicklungsrechner geprüften Stand.

| Bibliothek | Version (geprüft) | Grenze | Zweck | Lizenz |
|---|---|---|---|---|
| Streamlit | 1.67.0 | ≥1.50, <1.68 | Oberfläche, lokaler Webserver | Apache 2.0 |
| streamlit-image-coordinates | 0.4.x | ≥0.4.1, <0.5 | Klicks in der Vorschau | MIT |
| PyArrow | 22.0.0 | ≥14, <23 | von Streamlit benötigt | Apache 2.0 |
| PyMuPDF | 1.28.2 | ≥1.28.2, <2.0 | PDF lesen, schwärzen, bereinigen | **AGPL 3.0** (oder kommerziell) |
| EasyOCR | 1.7.2 | ≥1.7.2, <1.8 | Texterkennung | Apache 2.0 |
| PyTorch (über EasyOCR) | 2.15.0 | ohne Grenze | Rechenbibliothek der Texterkennung | BSD |
| spaCy + Modelle de_core_news | 3.5.4 / 3.5.0 | ≥3.5.0, <3.6.0 | Erkennung von Namen und Orten | MIT |
| numpy | 1.26.4 | <2 | Rechenbibliothek | BSD |
| Pillow | 13.0.0 | ohne Grenze | Bilder | MIT-CMU (HPND) |
| Faker | – | ohne Grenze | wird nicht genutzt (Überbleibsel, kann entfallen) | MIT |

Hinzu kommen deren Unterabhängigkeiten (u. a. OpenCV, scikit-image, Tornado).

**Zur AGPL:** Die AGPL verpflichtet bei Weitergabe oder bei Bereitstellung über ein Netzwerk für andere zur Offenlegung des Quellcodes. Grauzone ist selbst quelloffen, läuft nur lokal und liefert PyMuPDF nicht mit. Ob das für den dienstlichen Einsatz reicht, sollte die IT bzw. das Lizenzmanagement bewerten.

**Bekannter Versionsstand:** spaCy 3.5 erzwingt Python 3.11 und numpy 1.x. Das ist eine ältere, aber gepflegte Versionskette. Einige Bibliotheken sind bewusst nach oben begrenzt, weil neuere Versionen nachweislich Fehler verursachen (z. B. verschiebt PyMuPDF 2.x Text unter die Balken). Sicherheitsupdates innerhalb der Grenzen werden bei einer Neueinrichtung übernommen, darüber hinaus nicht automatisch.

## 8. Risiken und Bewertung aus Sicht des Entwicklers

| Thema | Bewertung | Möglicher Umgang |
|---|---|---|
| Unvollständige Erkennung (z. B. Handschrift, schlechte Scans, ungewöhnliche Formate) | fachliches Hauptrisiko | Jede Seite prüfen; Markieren von Hand; Prüfprotokoll nutzen |
| Installation per `curl … \| sh` (uv) und Downloads aus öffentlichen Quellen | Lieferkette | Installation durch die IT aus geprüften Quellen oder einem internen Spiegel; `uv` zentral bereitstellen |
| Keine Lockdatei mit Hashes | Lieferkette, Reproduzierbarkeit | Lockdatei ergänzen (Aufwand gering) oder Installation einmal prüfen und einfrieren |
| Selbst-Update ohne Signatur | Manipulation bei Kompromittierung des GitHub-Kontos | Versionsabfrage abschalten (`.keine-updatepruefung`), Updates nur über die IT |
| App nicht signiert und nicht notarisiert | Herkunft für macOS nicht belegt | Code prüfen (öffentlich) und intern freigeben |
| Lokaler Server ohne Anmeldung | auf Rechnern, an denen mehrere Personen gleichzeitig angemeldet sind, könnte ein anderes Konto `localhost:8501` erreichen | nur auf Einzelplatzrechnern nutzen |
| Gelernte Begriffe im Klartext (`knowledge_base.json`) | kann Namen enthalten | Festplattenverschlüsselung (FileVault); Datenordner nicht in Sicherungen oder Synchronisierung einbeziehen, oder bewusst einbeziehen |
| Programmcode im Benutzerkonto beschreibbar | Änderungen durch Schadsoftware mit Benutzerrechten möglich | entspricht jedem im Benutzerkonto installierten Programm |
| Ältere Versionskette (Python 3.11, numpy 1.x) | geringeres Risiko, da keine Netzwerkdienste nach außen | bei Anhebung alle Grenzen gemeinsam testen |
| Ergebnisse ohne Tags | Barrierefreiheit | bewusst zugunsten des Datenschutzes |

## 9. Möglichkeiten für den Einsatz im Verwaltungsnetz

1. **Einzelplatz mit Internet bei der Einrichtung:**
   - Einrichtung wie vorgesehen.
   - Danach Versionsabfrage abschalten und ausgehende Verbindungen des Programms sperren.
   - Das Programm arbeitet dann vollständig offline.
2. **Installation durch die IT ohne Internet am Arbeitsplatz:**
   - Die IT lädt Python 3.11, die Bibliotheken (Wheels) und die Modelle einmal herunter und prüft sie.
   - Die IT installiert aus einem lokalen Verzeichnis oder internen Spiegel (`uv pip install --no-index --find-links …`).
   - Die Texterkennungs-Modelle werden nach `~/.EasyOCR/model/` kopiert.
   - Updates nur über die IT.
3. **Prüfung des Codes:**
   - Der eigene Code ist mit etwa 2.200 Zeilen überschaubar und öffentlich.
   - Die Tests liegen im Ordner `tests/` (95 Regressionstests mit erfundenen Daten).

Auf Wunsch kann der Entwickler eine Lockdatei mit festen Versionen und Hashes sowie ein Installationspaket für die Offline-Installation vorbereiten.

## 10. Prüffragen für die IT

- [ ] Ist der Betrieb einer lokalen Python-Anwendung im Benutzerkonto (ohne Admin-Rechte) zulässig?
- [ ] Dürfen die Quellen aus Abschnitt 4.1 für die Einrichtung genutzt werden, oder ist eine Installation aus internen Quellen nötig?
- [ ] Soll die Versionsabfrage bei GitHub abgeschaltet und gesperrt werden?
- [ ] Ist die AGPL-Lizenz von PyMuPDF für diesen Einsatz akzeptabel?
- [ ] Ist eine nicht signierte, nicht notarisierte App nach Codeprüfung freigabefähig?
- [ ] Ist der Rechner ein Einzelplatzrechner (Abschnitt 8, lokaler Server)?
- [ ] Ist die Festplatte verschlüsselt, und wie soll der Datenordner bei Sicherungen behandelt werden?
- [ ] Wer ist für Updates und die Prüfung neuer Versionen zuständig?

## 11. Windows

Eine Windows-Fassung gibt es derzeit nicht. Technisch ist sie möglich:
- Alle Bibliotheken gibt es für Windows.
- Der Programmcode selbst ist nicht an macOS gebunden.

Neu zu schreiben wären die Start-, Einrichtungs- und Update-Skripte (heute macOS-Shell-Skripte). Für Windows-Arbeitsplätze im Verwaltungsnetz wäre eine von der IT durchgeführte Installation (Abschnitt 9, Nr. 2) der naheliegende Weg; Richtlinien wie AppLocker können Python im Benutzerkonto sonst blockieren.

## 12. Angaben selbst nachprüfen (macOS)

Lauschende Verbindungen (erwartet: nur `localhost:8501`):

```bash
lsof -nP -iTCP:8501 -sTCP:LISTEN
```

Ausgehende Verbindungen des laufenden Programms (erwartet: keine nach dem Start):

```bash
lsof -nP -i | grep -i python
```

Versionsabfrage abschalten:

```bash
touch ~/Library/Application\ Support/Grauzone\ PRO/.keine-updatepruefung
```

Installierte Bibliotheken und Versionen:

```bash
~/.local/bin/uv pip list --python ~/Library/Application\ Support/Grauzone\ PRO/venv/bin/python
```

Netzwerkzugriffe im Quellcode suchen:

```bash
grep -nE "http|curl|urllib|requests|socket" app.py erkennung.py macos/*.sh
```
