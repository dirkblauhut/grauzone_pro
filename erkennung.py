"""Erkennung personenbezogener Daten auf Wortebene.

Ablauf je PDF-Seite:
  1. Wörter mit Position holen – aus der Textebene des PDFs oder, bei
     gescannten Seiten, per Texterkennung (EasyOCR).
  2. Aus den Wörtern den Seitentext zusammensetzen und darin Fundstellen
     suchen (spaCy-Sprachmodell, Muster für Telefon, E-Mail, IBAN,
     Anschrift, Anrede, Vornamenliste, gelernte Begriffe).
  3. Jede Fundstelle auf die Wörter abbilden, die sie abdeckt. Geschwärzt
     werden nur diese Wörter, nicht die ganze Zeile.

Alle Positionen sind PDF-Punkte (1/72 Zoll) im Koordinatensystem von PyMuPDF.
Das Modul kennt kein Streamlit und lässt sich daher einzeln testen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Wort:
    text: str
    rect: tuple[float, float, float, float]   # x0, y0, x1, y1 in PDF-Punkten
    start: int = 0                             # Position im Seitentext
    ende: int = 0
    ocr: bool = False                          # Position stammt aus Texterkennung
    geteilt: bool = False                      # aus mehrteiligem OCR-Stück geschätzt


@dataclass
class Fund:
    text: str
    art: str                                   # PER, ORT, ORG, TEL, MAIL, IBAN, ADR, LISTE
    woerter: list[int] = field(default_factory=list)
    start: int = 0
    ende: int = 0


ARTEN = {
    "PER": "Person", "ORT": "Ort", "ORG": "Organisation", "TEL": "Telefon",
    "MAIL": "E-Mail", "IBAN": "IBAN", "ADR": "Anschrift", "LISTE": "gelernt",
}

# --- 1. Wörter holen ----------------------------------------------------------

def woerter_aus_textebene(page) -> list[list[Wort]]:
    """Wörter aus der Textebene, gruppiert nach Zeilen."""
    zeilen: dict[tuple[int, int], list[Wort]] = {}
    for x0, y0, x1, y1, txt, block, zeile, _ in page.get_text("words", sort=True):
        if txt.strip():
            zeilen.setdefault((block, zeile), []).append(Wort(txt, (x0, y0, x1, y1)))
    return [sorted(z, key=lambda w: w.rect[0]) for z in zeilen.values()]


def woerter_aus_ocr(reader, page, zoom: float = 2.5) -> list[list[Wort]]:
    """Wörter per Texterkennung, gruppiert nach Zeilen.

    Mit kleinem width_ths liefert EasyOCR meist einzelne Wörter. Enthält ein
    Stück doch mehrere Wörter, wird es anhand der Zeichenzahl anteilig zerlegt;
    solche Positionen sind ungenau und bekommen beim Schwärzen mehr Rand.
    """
    import pymupdf
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    bild = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        bild = bild[:, :, :3]
    stuecke = []
    for box, txt, _sicherheit in reader.readtext(bild, width_ths=0.05):
        xs = [p[0] / zoom for p in box]
        ys = [p[1] / zoom for p in box]
        stuecke.append((min(xs), min(ys), max(xs), max(ys), txt))

    woerter: list[Wort] = []
    for x0, y0, x1, y1, txt in stuecke:
        teile = txt.split()
        if not teile:
            continue
        gesamt = len(txt)
        breite = (x1 - x0) / max(gesamt, 1)
        pos = 0
        for teil in teile:
            i = txt.index(teil, pos)
            if len(teile) == 1:
                rect = (x0, y0, x1, y1)
            else:
                rect = (x0 + i * breite, y0, x0 + (i + len(teil)) * breite, y1)
            woerter.append(Wort(teil, rect, ocr=True, geteilt=len(teile) > 1))
            pos = i + len(teil)

    # In Zeilen gruppieren: gleiche Höhe (Mittelpunkt innerhalb halber Zeilenhöhe)
    zeilen: list[list[Wort]] = []
    for w in sorted(woerter, key=lambda w: (w.rect[1] + w.rect[3]) / 2):
        mitte = (w.rect[1] + w.rect[3]) / 2
        hoehe = w.rect[3] - w.rect[1]
        if zeilen:
            ref = zeilen[-1][0]
            ref_mitte = (ref.rect[1] + ref.rect[3]) / 2
            if abs(mitte - ref_mitte) < max(hoehe, ref.rect[3] - ref.rect[1]) / 2:
                zeilen[-1].append(w)
                continue
        zeilen.append([w])
    return [sorted(z, key=lambda w: w.rect[0]) for z in zeilen]


def seitentext(zeilen: list[list[Wort]]) -> tuple[str, list[Wort]]:
    """Setzt den Seitentext zusammen und merkt sich jede Wortposition."""
    teile, woerter, pos = [], [], 0
    for z in zeilen:
        for i, w in enumerate(z):
            if i:
                teile.append(" ")
                pos += 1
            w.start, w.ende = pos, pos + len(w.text)
            teile.append(w.text)
            pos = w.ende
            woerter.append(w)
        teile.append("\n")
        pos += 1
    return "".join(teile), woerter


# --- 2. Fundstellen suchen ------------------------------------------------------

GROSS = r"[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?"
MUSTER = [
    # Anrede + Name: "Frau Erika Mustermann", "Herrn Dr. Thomas Beispiel"
    ("PER", re.compile(rf"\b(?:Herrn?|Frau|Fr\.|Hr\.)\s+(?:(?:Dr|Prof)\.\s+)*((?:{GROSS})(?:[ \t]+{GROSS}){{0,2}})")),
    # Feldbezeichnung + Name: "Absender: Max Beispiel" (Prüfung auf Stoppwörter in finde)
    ("PER_FELD", re.compile(
        rf"\b(?:Absender(?:in)?|Empf\u00e4nger(?:in)?|Name|Vorname|Nachname|Antragsteller(?:in)?|"
        rf"Ansprechpartner(?:in)?|Sachbearbeiter(?:in)?|Betroffene[rn]?|Kunde|Kundin)[ \t]*:[ \t]*"
        rf"((?:{GROSS})(?:[ \t]+{GROSS}){{0,2}})")),
    # Name über Zeilenumbruch: "Herrn Max⏎Beispiel" (Folgewort wird in finde geprüft)
    ("PER_UMBRUCH", re.compile(rf"\b(?:Herrn?|Frau|Fr\.|Hr\.)[ \t]+(?:(?:Dr|Prof)\.[ \t]+)*(?:{GROSS})[ \t]*\n[ \t]*({GROSS})")),
    # Telefon/Fax: beginnt mit 0 oder +, mind. 6 Ziffern, keine Datumsangabe
    ("TEL", re.compile(r"(?<![\w.])(?:\+\d{1,3}[ \t]?(?:\(0\))?[ \t]?|0)\d{2,5}(?:[ \t/\-]?\d{2,}){1,4}(?![\w.])")),
    ("MAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    # IBAN, auch mit typischen OCR-Verwechslungen (O/o statt 0, I/l statt 1); Prüfung in finde
    ("IBAN", re.compile(r"\b[A-Z]{2}[\dOo]{2}(?:[ \t]?[A-Za-z0-9]{4}){3,7}(?:[ \t]?[A-Za-z0-9]{1,4})?\b")),
    # Postleitzahl + Ort
    ("ADR", re.compile(rf"\b\d{{5}}[ \t]+{GROSS}(?:[ \t\-]{GROSS})?")),
    # Straße + Hausnummer
    ("ADR", re.compile(
        r"\b[A-ZÄÖÜ][\wäöüß\-]*(?:straße|strasse|str\.|weg|allee|platz|gasse|ring|damm|ufer|chaussee|pfad|steig|markt)"
        r"[ \t]+\d+[ \t]?[a-zA-Z]?\b"
        r"|\b(?:Am|An der|Auf dem|Im|In der|Zum|Zur)[ \t]+[A-ZÄÖÜ][\wäöüß\-]+[ \t]+\d+[ \t]?[a-zA-Z]?\b")),
]
SPACY_ARTEN = {"PER": "PER", "LOC": "ORT", "ORG": "ORG"}
# Großgeschriebene Wörter, die am Zeilenanfang folgen können und keine Namen sind
NICHT_NAME = {
    "Ihr", "Ihre", "Ihren", "Ihrem", "Ihrer", "Ihres", "Sie", "Der", "Die", "Das", "Den", "Dem",
    "Des", "Ein", "Eine", "Einen", "Mit", "Und", "Oder", "Bei", "Von", "Vom", "Zu", "Zum", "Zur",
    "Für", "Auf", "Aus", "Nach", "Wir", "Er", "Es", "Im", "In", "Am", "An", "Betreff", "Datum",
    "Telefon", "Fax", "Mail", "Tel", "Az", "Aktenzeichen", "Anlage", "Anlagen", "Hinweis",
}
_OCR_ZIFFER = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5", "B": "8", "Z": "2"})
ANREDE = re.compile(r"(?:(?:Herrn?|Frau|Fr\.|Hr\.|Dr\.|Prof\.)[ \t]+)+")


def _ist_datum(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", s.strip()))


rx_mail = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _ist_iban(s: str) -> bool:
    """Prüft nach Ersatz typischer OCR-Verwechslungen, ob es wie eine IBAN aussieht."""
    z = re.sub(r"\s+", "", s)
    n = z[:2] + z[2:].translate(_OCR_ZIFFER)
    return len(n) >= 15 and sum(c.isdigit() for c in n) >= 12 and n[2:4].isdigit()


def finde(text: str, woerter: list[Wort], nlp, vornamen: set[str], gelernt: list[str]) -> list[Fund]:
    spans: list[tuple[int, int, str]] = []

    if nlp is not None:
        for ent in nlp(text).ents:
            art = SPACY_ARTEN.get(ent.label_)
            if not art:
                continue
            # Fundstellen nie über Zeilenumbrüche ziehen (sonst z. B.
            # Absender und Anschrift als eine Stelle)
            pos = ent.start_char
            for teil in text[ent.start_char:ent.end_char].split("\n"):
                spans.append((pos, pos + len(teil), art))
                pos += len(teil) + 1

    for art, rx in MUSTER:
        for m in rx.finditer(text):
            gruppe = 1 if m.lastindex else 0
            s, e = m.span(gruppe)
            if art == "PER_FELD":
                if m.group(1).split()[0] in NICHT_NAME:
                    continue
                art = "PER"
            if art == "PER_UMBRUCH":
                if m.group(1) in NICHT_NAME:
                    continue
                art = "PER"
            if art == "IBAN" and not _ist_iban(m.group(0)):
                continue
            if art == "TEL" and (_ist_datum(m.group(0)) or sum(c.isdigit() for c in m.group(0)) < 6):
                continue
            spans.append((s, e, art))

    # E-Mail-Adressen nach Texterkennung: Wort mit "@" immer ganz erfassen; fehlt der
    # Punkt vor der Endung ("example org"), die Endung als Folgewort anhängen
    for i, w in enumerate(woerter):
        if "@" in w.text and not rx_mail.fullmatch(w.text.strip(".,;:")):
            ende = w.ende
            if "." not in w.text.split("@", 1)[1].strip(".,;:") and i + 1 < len(woerter) \
                    and re.fullmatch(r"[a-z]{2,4}[.,;:]?", woerter[i + 1].text) \
                    and text[w.ende:woerter[i + 1].start].strip() == "":
                ende = woerter[i + 1].ende
            spans.append((w.start, ende, "MAIL"))

    # Vornamenliste: Vorname + folgendes großgeschriebenes Wort
    for i, w in enumerate(woerter):
        if w.text.strip(".,;:").lower() in vornamen:
            ende = w.ende
            if i + 1 < len(woerter) and re.fullmatch(GROSS + r"[.,;:]?", woerter[i + 1].text) \
                    and text[w.ende:woerter[i + 1].start].strip() == "":
                ende = woerter[i + 1].ende
            spans.append((w.start, ende, "PER"))

    # Gelernte Begriffe (Blacklist)
    for begriff in gelernt:
        if len(begriff.strip()) < 2:
            continue
        for m in re.finditer(r"(?<!\w)" + re.escape(begriff.strip()) + r"(?!\w)", text, re.IGNORECASE):
            spans.append((m.start(), m.end(), "LISTE"))

    # Satzzeichen am Rand abschneiden, überlappende Stellen zusammenfassen
    bereinigt = []
    for s, e, art in spans:
        while s < e and text[s] in " \t\n.,;:()\"'":
            s += 1
        while e > s and text[e - 1] in " \t\n.,;:()\"'":
            e -= 1
        if art == "PER":   # Anrede und Titel bleiben lesbar
            m = ANREDE.match(text, s, e)
            if m and m.end() < e:
                s = m.end()
        if e > s:
            bereinigt.append((s, e, art))
    bereinigt.sort()
    zusammen: list[list] = []
    rang = ["LISTE", "IBAN", "MAIL", "TEL", "PER", "ADR", "ORT", "ORG"]
    for s, e, art in bereinigt:
        if zusammen and s < zusammen[-1][1]:
            letzte = zusammen[-1]
            letzte[1] = max(letzte[1], e)
            if rang.index(art) < rang.index(letzte[2]):
                letzte[2] = art
        else:
            zusammen.append([s, e, art])

    funde = []
    for s, e, art in zusammen:
        idx = [i for i, w in enumerate(woerter) if w.start < e and w.ende > s]
        if idx:
            funde.append(Fund(text[s:e].replace("\n", " "), art, idx, s, e))
    return funde


def wort_rechteck(wort: Wort, fund: Fund) -> tuple[float, float, float, float]:
    """Rechteck nur für den Teil des Wortes, der zur Fundstelle gehört.

    Beispiel: Das Wort "Mustermann," gehört ohne Komma zur Fundstelle; das
    Komma bleibt stehen. Die Breite wird anteilig nach Zeichen berechnet.
    """
    x0, y0, x1, y1 = wort.rect
    n = max(len(wort.text), 1)
    a = max(fund.start, wort.start) - wort.start
    b = min(fund.ende, wort.ende) - wort.start
    breite = (x1 - x0) / n
    if wort.ocr:
        # Positionen aus der Texterkennung sind ungenau. Ganze Wörter bekommen
        # 2 pt Rand; anteilig geschätzte Teile deutlich mehr, damit keine
        # Buchstabenreste stehen bleiben.
        zugabe = 0.8 * breite if (wort.geteilt or a > 0 or b < n) else 2.0
        return (x0 + a * breite - zugabe, y0 - 2.0, x0 + b * breite + zugabe, y1 + 2.0)
    zugabe = 0.35 * breite if (a > 0 or b < n) else 1.0
    return (max(x0 - 1.0, x0 + a * breite - zugabe), y0 - 1.0,
            min(x1 + 1.0, x0 + b * breite + zugabe), y1 + 1.0)


# --- 3. Export als Markdown -----------------------------------------------------

PLATZHALTER = {
    "PER": "Person", "ORT": "Ort", "ORG": "Organisation", "TEL": "Telefon",
    "MAIL": "E-Mail", "IBAN": "IBAN", "ADR": "Anschrift", "LISTE": "geschwärzt",
}
_MD_ZEICHEN = re.compile(r"([\\`*_\[\]<>#|~])")
_MD_ZEILENANFANG = re.compile(r"^(\s*)(?:([-+>=])|(\d+)([.)]))(?=\s|$)")


def _md_zeilenanfang(m) -> str:
    """Verhindert, dass eine Zeile als Liste, Zitat oder Überschrift gilt."""
    if m.group(2):
        return f"{m.group(1)}\\{m.group(2)}"
    return f"{m.group(1)}{m.group(3)}\\{m.group(4)}"


def _md_text(s: str) -> str:
    """Maskiert Zeichen, die Markdown sonst als Formatierung liest."""
    return _MD_ZEICHEN.sub(r"\\\1", s)


def markdown(seiten, gewaehlt, kopf: str = "", nicht_gescannt=()) -> tuple[str, int]:
    """Text der gescannten Seiten als Markdown, Fundstellen durch Platzhalter ersetzt.

    seiten:   Liste von (Seitenindex, Seitentext, Funde) wie aus seitentext/finde.
    gewaehlt: Funktion (Seitenindex, Fund) -> bool; nur gewählte Stellen werden ersetzt.
    Gleiche Angaben (gleiche Art, gleicher Text) bekommen im ganzen Dokument
    dieselbe Nummer, z. B. [Person 1]. Liefert (Markdown, Anzahl ersetzter Stellen).
    """
    nummern: dict[tuple[str, str], int] = {}
    zaehler: dict[str, int] = {}
    anzahl = 0
    teile = ["# Anonymisiertes Dokument", ""]
    if kopf:
        teile += [_md_text(kopf), ""]
    if nicht_gescannt:
        teile += ["> Nicht enthalten, da nicht gescannt: Seite "
                  + ", ".join(str(p + 1) for p in nicht_gescannt), ""]

    for p, text, funde in seiten:
        stuecke, pos = [], 0
        for f in sorted(funde, key=lambda f: f.start):
            if not gewaehlt(p, f) or f.start < pos:
                continue
            schluessel = (f.art, f.text.lower())
            if schluessel not in nummern:
                zaehler[f.art] = zaehler.get(f.art, 0) + 1
                nummern[schluessel] = zaehler[f.art]
            stuecke.append(_md_text(text[pos:f.start]))
            stuecke.append(f"[{PLATZHALTER.get(f.art, 'geschwärzt')} {nummern[schluessel]}]")
            pos = f.ende
            anzahl += 1
        stuecke.append(_md_text(text[pos:]))
        zeilen = []
        for zeile in "".join(stuecke).split("\n"):
            zeile = zeile.rstrip()
            if zeile:
                zeilen.append(_MD_ZEILENANFANG.sub(_md_zeilenanfang, zeile))
        teile += ["---", "", f"## Seite {p + 1}", ""]
        teile.append("  \n".join(zeilen) if zeilen else "*(kein Text)*")
        teile.append("")
    return "\n".join(teile), anzahl


# --- 4. Export bereinigen und prüfen --------------------------------------------

def bereinige_pdf(doc) -> None:
    """Entfernt, was apply_redactions() und set_metadata() nicht erfassen.

    Dazu gehören XMP-Metadaten (zweiter Metadatensatz neben dem Info-Wörterbuch),
    Lesezeichen und eingebettete Dateien. Alle drei können Namen enthalten.
    """
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
    try:
        doc.set_toc([])
    except Exception:
        pass
    for name in list(doc.embfile_names()):
        try:
            doc.embfile_del(name)
        except Exception:
            pass


def pruefe_export(daten: bytes, rechtecke: dict[int, list[tuple[float, float, float, float]]]) -> list[str]:
    """Prüft das fertige PDF und liefert Meldungen (leer = nichts gefunden).

    Die Meldungen nennen nur Art und Seite, nie den geschwärzten Text.
    rechtecke: Seitenindex (0-basiert) -> Rechtecke, die geschwärzt sein müssen.
    Geprüft wird (1) Text unter den Balken, (2) Helligkeit der Balken im gerenderten
    Bild (deckt Scans ab), (3) Metadaten, XMP, Lesezeichen, eingebettete Dateien,
    (4) verbliebene Anmerkungen und Formularfelder.
    """
    import pymupdf
    meldungen: list[str] = []
    try:
        doc = pymupdf.open(stream=daten, filetype="pdf")
    except Exception:
        return ["Das exportierte PDF lässt sich nicht erneut öffnen."]
    try:
        for p, liste in sorted(rechtecke.items()):
            if p >= len(doc):
                meldungen.append(f"Seite {p + 1} fehlt im Export.")
                continue
            page = doc[p]
            unter_balken = hell = 0
            for r in liste:
                rect = pymupdf.Rect(*r)
                innen = rect + (1.0, 1.0, -1.0, -1.0)   # Randzeichen der Nachbarwörter nicht mitzählen
                if innen.is_empty:
                    continue
                # Satzzeichen neben dem Fund bleiben absichtlich stehen und zählen nicht
                if any(c.isalnum() for c in page.get_text("text", clip=innen)):
                    unter_balken += 1
                try:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=innen, colorspace=pymupdf.csGRAY)
                    if pix.samples and sum(pix.samples) / len(pix.samples) > 60:
                        hell += 1
                except Exception:
                    hell += 1
            if unter_balken:
                meldungen.append(f"Seite {p + 1}: {unter_balken} Stelle(n) mit Text unter dem Balken.")
            if hell:
                meldungen.append(f"Seite {p + 1}: {hell} Balken im Bild nicht vollständig schwarz.")
        if any(str(v).strip() for k, v in (doc.metadata or {}).items() if k not in ("format", "encryption") and v):
            meldungen.append("Dokumenteigenschaften (Autor, Titel o. ä.) nicht leer.")
        if (doc.get_xml_metadata() or "").strip():
            meldungen.append("XMP-Metadaten nicht leer.")
        if doc.get_toc():
            meldungen.append("Lesezeichen vorhanden.")
        if doc.embfile_names():
            meldungen.append("Eingebettete Dateien vorhanden.")
        anm = sum(1 for page in doc for _ in page.annots())
        if anm:
            meldungen.append(f"{anm} Anmerkung(en) vorhanden.")
        felder = sum(1 for page in doc for _ in page.widgets())
        if felder:
            meldungen.append(f"{felder} Formularfeld(er) vorhanden.")
    finally:
        doc.close()
    return meldungen
