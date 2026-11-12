# 🛡️ Grauzone PRO: Lokale PDF-Anonymisierung

Grauzone PRO erkennt und schwärzt personenbezogene Daten (Namen, Orte, Organisationen, Telefonnummern) in PDF-Dokumenten.

**Alles läuft lokal auf dem eigenen Rechner.** Dokumente werden nicht in eine Cloud hochgeladen. Internet braucht es bei der Einrichtung, um Programmbibliotheken und KI-Modelle herunterzuladen. Die Mac-App fragt außerdem beim Start bei GitHub die neueste Versionsnummer ab (abschaltbar, keine Dokumentinhalte).

---

## ✨ Funktionen

- **Schwärzt nur, was nötig ist:** Geschwärzt werden einzelne Namen, Anschriften oder Nummern, nicht ganze Zeilen. Anrede („Frau“, „Herr“) und der übrige Text bleiben lesbar.
- **Erkennung:** spaCy-Sprachmodell (`de_core_news_lg`, ersatzweise `de_core_news_sm`) für Personen, Orte und Organisationen, dazu feste Muster für Telefon- und Faxnummern, E-Mail-Adressen, IBAN, Straße mit Hausnummer, Postleitzahl mit Ort, Namen nach „Herr/Frau“ und eine Vornamenliste. Datumsangaben gelten nicht als Telefonnummer.
- **Textebene oder Texterkennung:** Hat das PDF eine Textebene, nutzt Grauzone deren genaue Wortpositionen. Gescannte Seiten liest EasyOCR. Für PDFs mit eingefügten Bildern lässt sich die Texterkennung in der Seitenleiste erzwingen.
- **Mehrseitig:** „Alle Seiten“ scannt das ganze Dokument; beim Export werden alle gescannten Seiten geschwärzt. Nicht gescannte Seiten werden vorher deutlich gemeldet.
- **Durch mehrseitige PDFs scrollen:** Die Vorschau zeigt alle Seiten untereinander. Mit den Pfeilen ◀ ▶, der Seitenzahl in der Seitenleiste oder „Bearbeiten“ an einer Seite springt die Vorschau zur gewählten Seite; rechts stehen deren Fundstellen. Der Scrollbereich passt sich der Fensterhöhe an. Abschaltbar in der Seitenleiste („Alle Seiten untereinander zeigen“).
- **Prüfen und korrigieren:** Jede Fundstelle steht mit Art (Person, Anschrift, Telefon …) in einer Liste und ist in der Vorschau rot markiert. Abwählen = bleibt stehen; fehlende Begriffe lassen sich eintippen.
- **Lernt mit:** Abgewählte Stellen („nie schwärzen“) und eingetippte Begriffe („immer schwärzen“) merkt sich `knowledge_base.json` für künftige Dokumente.
- **Sauberer Export:** Der Text unter den Balken wird aus dem PDF entfernt (bei Scans die Bildpunkte), die Dokument-Metadaten (Autor, Titel), XMP-Metadaten, Lesezeichen und eingebettete Dateien werden gelöscht. Nach dem Export prüft Grauzone das fertige PDF noch einmal (Text und Helligkeit unter den Balken, Metadaten, Lesezeichen, Anhänge, Anmerkungen, Formularfelder) und meldet Auffälligkeiten. Formularfelder und Anmerkungen werden vorher fest in die Seite übernommen, damit auch ihr Text unter den Balken verschwindet; im Ergebnis sind die Felder nicht mehr ausfüllbar.
- **Export als Markdown:** Zusätzlich zum PDF lässt sich der Text der gescannten Seiten als `.md`-Datei herunterladen. Geschwärzte Stellen stehen dort als Platzhalter wie `[Person 1]` oder `[Anschrift 2]`; gleiche Angaben tragen im ganzen Dokument dieselbe Nummer. Tabellen und Layout bleiben dabei nicht erhalten.

> Die Erkennung ist eine Hilfe, keine Garantie. Vor dem Weitergeben jede Seite selbst durchsehen.

---

## 💿 Installation auf dem Mac per DMG (am einfachsten)

1. Unter **[Releases](https://github.com/dirkblauhut/grauzone_pro/releases/latest)** die Datei **`Grauzone-PRO-<Version>.dmg`** herunterladen und doppelklicken.
2. **Grauzone PRO** auf den Ordner **Programme** ziehen.
3. Grauzone PRO im Programme-Ordner öffnen. Die App ist nicht bei Apple notarisiert, deshalb fragt macOS beim ersten Mal nach:
   - macOS 14 und älter: **Rechtsklick → „Öffnen“ → „Öffnen“**,
   - macOS 15 und neuer: **Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“**.
4. Beim ersten Start öffnet sich ein Terminalfenster und lädt einmalig Python 3.11, Bibliotheken und KI-Modelle (ca. 2 GB, 5–15 Minuten). Danach öffnet sich Grauzone im Browser unter <http://localhost:8501>. Später startet die App in wenigen Sekunden.

**Updates:** Ab Version 0.4.0 sucht Grauzone beim Start nach einer neuen Version und fragt im Terminalfenster, ob sie installiert werden soll. Eine neue DMG und eine erneute Freigabe in macOS sind dafür nicht nötig. Abschalten lässt sich das in der Seitenleiste („Beim Start nach neuen Versionen suchen“).

Beenden: Schaltfläche „Beenden“ in der Seitenleiste (danach das Terminalfenster schließen) oder das Terminalfenster schließen. Python-Umgebung, Wissensbasis und Vornamenliste liegen in `~/Library/Application Support/Grauzone PRO`. Zum vollständigen Entfernen die App und diesen Ordner löschen.

Die DMG enthält nur einen kleinen Starter, keine Python-Bibliotheken. Sie wird mit `sh macos/build_dmg.sh` gebaut (Ergebnis in `dist/`, Icon: `macos/make_icon.py`) und als Anhang an ein GitHub-Release gehängt.

---

## 🚀 Installation auf dem Mac aus dem Quellcode (ohne Terminal)

1. Auf dieser Seite oben **„Code“ → „Download ZIP“** wählen, die ZIP-Datei entpacken und den Ordner an einen festen Platz legen, z. B. `Dokumente/grauzone_pro`.
2. Im Ordner **`Grauzone installieren.command`** doppelklicken.
   - Meldet macOS, die Datei stamme von einem nicht verifizierten Entwickler: **Rechtsklick → „Öffnen“ → „Öffnen“**. (Ab macOS 15: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“.)
3. Es öffnet sich ein Terminalfenster. Die Einrichtung läuft von selbst durch (beim ersten Mal 5–15 Minuten, ca. 2 GB Download):
   - holt das Hilfsprogramm [uv](https://docs.astral.sh/uv/), das bei Bedarf auch **Python 3.11** herunterlädt (eine vorhandene Python-Installation wird nicht verändert),
   - legt im Ordner eine eigene Umgebung `venv` an und installiert dort die Bibliotheken,
   - lädt die deutschen spaCy-Modelle und die EasyOCR-Modelle,
   - startet Grauzone im Browser unter <http://localhost:8501>.
4. **Künftig:** Doppelklick auf **`START_GRAUZONE.command`**. Beenden: Schaltfläche „Beenden“ in der Seitenleiste oder Terminalfenster schließen.

Das Installationsprogramm kann jederzeit erneut ausgeführt werden, etwa nach einem Update. Vorhandenes wird nur ergänzt.

---

## 🛠️ Manuelle Installation (Mac, Linux, Windows)

**Voraussetzung: Python 3.9 bis 3.11.** spaCy 3.5 läuft nicht mit Python 3.12 oder neuer.

```bash
git clone https://github.com/dirkblauhut/grauzone_pro.git
cd grauzone_pro
```

Umgebung anlegen und aktivieren – Mac/Linux:

```bash
python3.11 -m venv venv
source venv/bin/activate
```

Windows:

```bat
py -3.11 -m venv venv
venv\Scripts\activate
```

Bibliotheken und Modelle installieren, dann starten:

```bash
python setup_project.py
python -m streamlit run app.py
```

`setup_project.py` installiert die Bibliotheken aus `requirements.txt` und beide deutschen Sprachmodelle. Grauzone verwendet automatisch das große Modell `de_core_news_lg`, das Namen zuverlässiger erkennt, und sonst `de_core_news_sm`.

> **Hinweis:** `python -m spacy download …` funktioniert mit spaCy 3.5 nicht mehr (es entsteht ein ungültiger Link mit Fehler 404). Die Modelle deshalb direkt installieren:
> `pip install https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-3.5.0/de_core_news_lg-3.5.0-py3-none-any.whl`

---

## 📦 Paketierung als Desktop-App (.app / .exe)

Für Rechner ohne Python lässt sich mit PyInstaller eine eigenständige App bauen (im aktivierten `venv`):

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed \
  --additional-hooks-dir=./hooks \
  --collect-all easyocr \
  --collect-all spacy \
  --collect-all de_core_news_lg \
  --add-data "app.py:." \
  --add-data "erkennung.py:." \
  --add-data "vornamen.txt:." \
  --add-data "knowledge_base.json:." \
  run_app.py
```

Die fertige App liegt danach im Ordner `dist/`. `vornamen.txt` und `knowledge_base.json` müssen dafür vorhanden sein.

---

## 📂 Projektstruktur

| Datei | Zweck |
|---|---|
| `macos/` | Bausteine der Mac-App: Starter, Einrichtungsskript, Icon, `build_dmg.sh` |
| `LICENSE` | MIT-Lizenz |
| `Grauzone installieren.command` | Einrichtung und Start per Doppelklick (macOS) |
| `START_GRAUZONE.command` | Start per Doppelklick nach der Einrichtung (`starten.command` ist gleichwertig) |
| `app.py` | Hauptanwendung (Streamlit-Oberfläche) |
| `erkennung.py` | Erkennung der Fundstellen auf Wortebene (ohne Oberfläche, einzeln testbar) |
| `requirements.txt` | Benötigte Bibliotheken |
| `setup_project.py` | Einfaches Installationsskript (Bibliotheken + kleines Sprachmodell) |
| `run_app.py` | Starter für die PyInstaller-App |
| `hooks/` | Konfiguration für den PyInstaller-Build |
| `.streamlit/config.toml` | Schaltet die Nutzungsstatistik von Streamlit ab |
| `vornamen.txt` | Vornamenliste für die Namenserkennung (lokal, nicht im Repository) |
| `knowledge_base.json` | Gelernte Begriffe (lokal, nicht im Repository) |

---

## 🔒 Datenschutz

- **Keine Cloud-Dienste:** Es werden keine externen KI-Dienste (z. B. OpenAI, Google Vision) angebunden.
- **Lokale Verarbeitung:** Texterkennung und Analyse laufen ausschließlich auf dem eigenen Rechner.
- **Keine Telemetrie:** Die Nutzungsstatistik von Streamlit ist über `.streamlit/config.toml` abgeschaltet.
- **Internet nur bei der Einrichtung:** für Bibliotheken, spaCy- und EasyOCR-Modelle. Danach arbeitet Grauzone offline.

---

## ⚖️ Lizenz

Grauzone PRO steht unter der [MIT-Lizenz](LICENSE), © 2026 Dirk Blauhut.

Die bei der Einrichtung geladenen Bibliotheken haben eigene Lizenzen, u. a. spaCy (MIT), EasyOCR und PyTorch (Apache 2.0 bzw. BSD), Streamlit (Apache 2.0) und PyMuPDF (AGPL-3.0 oder kommerziell). Sie werden nicht mit Grauzone ausgeliefert, sondern bei der Einrichtung direkt aus ihren Quellen installiert. Wer Grauzone samt Bibliotheken als Paket weitergibt (z. B. per PyInstaller), muss deren Lizenzbedingungen beachten, insbesondere die AGPL von PyMuPDF.
