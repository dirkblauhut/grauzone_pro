# 🛡️ Grauzone PRO: Lokale PDF-Anonymisierung

Grauzone PRO erkennt und schwärzt personenbezogene Daten (Namen, Anschriften, Telefonnummern, E-Mail-Adressen, Kennnummern, Geburtsdaten, Gesundheitsangaben) in PDF-Dokumenten.

**Alles läuft lokal auf dem eigenen Rechner.** Dokumente werden nicht in eine Cloud hochgeladen. Internet braucht es bei der Einrichtung, um Programmbibliotheken und KI-Modelle herunterzuladen. Die Mac-App fragt außerdem beim Start bei GitHub die neueste Versionsnummer ab (abschaltbar, keine Dokumentinhalte).

---

## ✨ Funktionen

- **Schwärzt nur, was nötig ist:** Geschwärzt werden einzelne Namen, Anschriften oder Nummern, nicht ganze Zeilen. Anrede („Frau“, „Herr“) und der übrige Text bleiben lesbar.
- **Erkennung:** spaCy-Sprachmodell (`de_core_news_lg`, ersatzweise `de_core_news_sm`) für Personen, Orte und Organisationen, dazu feste Muster für Telefon- und Faxnummern, E-Mail-Adressen, IBAN (mit Prüfziffer), Straße mit Hausnummer, Postleitzahl mit Ort, Namen nach „Herr/Frau“ und eine Vornamenliste.
- **Kennnummern:** Kunden-, Patienten-, Vertrags- und Versicherungsnummern, Steuer-ID und Steuernummer, Renten- und Krankenversicherungsnummer, Ausweis-, Pass- und Führerscheinnummer, Konto- und Kreditkartennummer, BIC, Kfz-Kennzeichen und IP-Adressen. Wo es eine Prüfziffer gibt, wird sie geprüft. Aktenzeichen und Vorgangsnummern bleiben lesbar.
- **Geburtsdatum und Gesundheit:** Ein Datum wird nur nach „geb.“, „geboren am“ oder „Geburtsdatum:“ geschwärzt, alle anderen Daten und Altersangaben bleiben stehen. Gesundheitsangaben (Diagnosen, Krankheiten, Medikamente, Behandlungen, Behinderungen) über Feldbezeichnungen wie „Diagnose:“, Wendungen wie „leidet an“, eine Wortliste und ICD-10-Codes.
- **Textebene oder Texterkennung:** Hat das PDF eine Textebene, nutzt Grauzone deren genaue Wortpositionen. Gescannte Seiten liest EasyOCR. Für PDFs mit eingefügten Bildern lässt sich die Texterkennung links unter „Analyse & Einstellungen“ erzwingen.
- **Mehrseitig:** „Alle Seiten scannen“ liest das ganze Dokument; beim Export werden alle gescannten Seiten geschwärzt. Nicht gescannte Seiten werden vorher deutlich gemeldet.
- **Durch mehrseitige PDFs scrollen:** Die Vorschau zeigt alle Seiten untereinander. Mit den Pfeilen ◀ ▶ und der Seitenzahl in der Werkzeugleiste über der Vorschau, „Fundstellen“ an einer Seite oder der Seitenübersicht links springt die Vorschau zur gewählten Seite; rechts stehen deren Fundstellen. Der Scrollbereich passt sich der Fensterhöhe an. Abschaltbar mit dem Schalter „Alle Seiten“ in der Werkzeugleiste.
- **Prüfen und korrigieren:** Jede Fundstelle steht mit Art und Begründung in einer Liste und ist in der Vorschau rot markiert. Unsichere Fundstellen stehen oben unter „Zu prüfen“. Abwählen = bleibt stehen; fehlende Begriffe lassen sich eintippen. Suche über alle Seiten, „Alle schwärzen/freigeben“ für Filter und Suche, gleiche Angaben auf allen Seiten gemeinsam entscheiden, Rückgängig und Wiederholen.
- **Ergebnis vergleichen:** Die Ansicht „Ergebnis“ zeigt das geschwärzte PDF zur aktuellen Auswahl, „Beide“ stellt es neben das Original.
- **Lernt mit:** Abgewählte Stellen („nie schwärzen“) und eingetippte Begriffe („immer schwärzen“) merkt sich `knowledge_base.json` für künftige Dokumente.
- **Sauberer Export:** Der Text unter den Balken wird aus dem PDF entfernt (bei Scans die Bildpunkte), die Dokument-Metadaten (Autor, Titel), XMP-Metadaten, Lesezeichen und eingebettete Dateien werden gelöscht. Nach dem Export prüft Grauzone das fertige PDF noch einmal (Text und Helligkeit unter den Balken, Metadaten, Lesezeichen, Anhänge, Anmerkungen, Formularfelder) und meldet Auffälligkeiten. Formularfelder und Anmerkungen werden vorher fest in die Seite übernommen, damit auch ihr Text unter den Balken verschwindet; im Ergebnis sind die Felder nicht mehr ausfüllbar.
- **Einzelne Seiten exportieren:** z. B. „1-3, 5“; leer heißt das ganze Dokument.
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

**Updates:** Ab Version 0.4.0 sucht Grauzone beim Start nach einer neuen Version und fragt im Terminalfenster, ob sie installiert werden soll. Eine neue DMG und eine erneute Freigabe in macOS sind dafür nicht nötig. Abschalten lässt sich das über ⚙️ rechts in der Kopfzeile („Beim Start nach neuen Versionen suchen“).

Beenden: Schaltfläche „Beenden“ in der Kopfzeile (danach das Terminalfenster schließen) oder das Terminalfenster schließen. Python-Umgebung, Wissensbasis und Vornamenliste liegen in `~/Library/Application Support/Grauzone PRO`. Zum vollständigen Entfernen die App und diesen Ordner löschen.

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
4. **Künftig:** Doppelklick auf **`START_GRAUZONE.command`**. Beenden: Schaltfläche „Beenden“ in der Kopfzeile oder Terminalfenster schließen.

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
| `tests/` | Automatische Tests (`./venv/bin/python -m unittest discover -s tests`) |
| `setup_project.py` | Einfaches Installationsskript (Bibliotheken + kleines Sprachmodell) |
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
