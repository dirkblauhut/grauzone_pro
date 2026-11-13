"""Erkennung personenbezogener Daten auf Wortebene.

Ablauf je PDF-Seite:
  1. Wörter mit Position holen – aus der Textebene des PDFs oder, bei
     gescannten Seiten, per Texterkennung (EasyOCR).
  2. Aus den Wörtern den Seitentext zusammensetzen und darin Fundstellen
     suchen (spaCy-Sprachmodell, Muster für Telefon, E-Mail, IBAN,
     Anschrift, Anrede, Vornamenliste, gelernte Begriffe).
  3. Jede Fundstelle auf die Wörter abbilden, die sie abdeckt. Geschwärzt
     werden nur diese Wörter, nicht die ganze Zeile.

Dazu kommen das Öffnen des PDFs (oeffne_pdf) und das Schwärzen beim Export
(schwaerze), damit Scan, Export und Tests denselben Weg nehmen.

Alle Positionen sind PDF-Punkte (1/72 Zoll) im Koordinatensystem von PyMuPDF.
Das Modul kennt kein Streamlit und lässt sich daher einzeln testen.
"""
from __future__ import annotations

import io
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
    art: str                                   # PER, ORT, ORG, TEL, MAIL, IBAN, ADR, KENN, GEB, GES, LISTE
    woerter: list[int] = field(default_factory=list)
    start: int = 0
    ende: int = 0
    quellen: tuple[str, ...] = ()              # wodurch erkannt, siehe BEGRUENDUNG


ARTEN = {
    "PER": "Person", "ORT": "Ort", "ORG": "Organisation", "TEL": "Telefon",
    "MAIL": "E-Mail", "IBAN": "IBAN", "ADR": "Anschrift", "KENN": "Kennnummer",
    "GEB": "Geburtsdatum", "GES": "Gesundheit", "LISTE": "gelernt", "HAND": "von Hand",
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
# Quelle je Muster (gleiche Reihenfolge wie MUSTER)
MUSTER_QUELLEN = ["ANREDE", "FELD", "UMBRUCH", "TEL", "MAIL", "IBAN", "PLZ", "STRASSE"]

# Warum eine Stelle als personenbezogen gilt (für die Fundstellenkarten)
BEGRUENDUNG = {
    "MODELL_PER": "Sprachmodell: Name einer Person",
    "MODELL_ORT": "Sprachmodell: Ort",
    "MODELL_ORG": "Sprachmodell: Organisation oder Institution",
    "ANREDE": "Name nach Anrede (Frau, Herr)",
    "FELD": "Name nach Feldbezeichnung (Absender:, Name: …)",
    "UMBRUCH": "Name nach Anrede, über Zeilenumbruch",
    "TEL": "Muster Telefon- oder Faxnummer",
    "MAIL": "Muster E-Mail-Adresse",
    "MAIL_OCR": "Wort mit @, E-Mail aus Texterkennung",
    "IBAN": "IBAN, Prüfziffer gültig",
    "IBAN_UNSICHER": "IBAN-ähnlich, Prüfziffer nicht bestätigt",
    "PLZ": "Postleitzahl mit Ort",
    "STRASSE": "Straße mit Hausnummer",
    "VORNAME": "Vorname aus der Vornamenliste",
    "LISTE": "gelernt: immer schwärzen",
    "KENN_FELD": "Kennnummer nach Feldbezeichnung (Kundennummer:, Vertragsnummer: …)",
    "KENN_PZ": "Kennnummer nach Feldbezeichnung, Prüfziffer gültig",
    "KENN_PZ_FALSCH": "Kennnummer nach Feldbezeichnung, Prüfziffer nicht bestätigt",
    "FORMAT_STEUER": "Format Steuer-ID, Prüfziffer gültig",
    "FORMAT_RV": "Format Rentenversicherungsnummer, Prüfziffer gültig",
    "FORMAT_KV": "Format Krankenversichertennummer, Prüfziffer gültig",
    "FORMAT_KARTE": "Format Kreditkartennummer, Prüfziffer gültig",
    "FORMAT_IP": "Format IP-Adresse",
    "GEB": "Datum nach „geb.“, „geboren am“ oder „Geburtsdatum:“",
    "GEBURTSORT": "Ort nach „Geburtsort:“",
    "GES_FELD": "Gesundheitsangabe nach Feldbezeichnung (Diagnose:, Medikation: …)",
    "GES_KONTEXT": "Gesundheitsangabe nach „leidet an“, „erkrankt an“ o. ä.",
    "GES_WORT": "Krankheit, Behinderung oder Medikament aus der Wortliste",
    "ICD": "ICD-10-Code",
    "BEGRIFF": "Begriff schwärzen (nur dieses Dokument)",
    "BEGRIFF_OCR": "ähnlich wie ein Begriff zum Schwärzen (Texterkennung)",
    "LISTE_OCR": "ähnlich wie ein gelernter Begriff (Texterkennung)",
    "FORMULARZEILE": "steht im Formular rechts neben einer Feldbezeichnung (Scan)",
}
# Quellen, die für sich allein eindeutig sind. Alle anderen (Sprachmodell, Vornamenliste,
# E-Mail aus Texterkennung, IBAN ohne gültige Prüfziffer) gelten als „zu prüfen“, solange
# nicht zwei verschiedene Quellen dieselbe Stelle finden. Keine Prozentwerte: spaCy
# liefert keine verlässlichen Wahrscheinlichkeiten.
EINDEUTIG = {"ANREDE", "FELD", "UMBRUCH", "TEL", "MAIL", "IBAN", "PLZ", "STRASSE", "LISTE",
             "KENN_FELD", "KENN_PZ", "GEB", "GEBURTSORT", "GES_FELD", "ICD", "BEGRIFF"}

# --- Kennnummern -----------------------------------------------------------------
# Vom Nutzer festgelegt (2026-11-12): Kunden-, Patienten- und Vertragsnummern sowie
# staatliche und finanzielle Kennnummern; Aktenzeichen, Vorgangs- und Fallnummern
# bleiben lesbar (Aktenzeichen der eigenen Behörde sind oft gewollt sichtbar).
# Feldbezeichnung -> Art der Prüfziffer (None = keine Prüfziffer bekannt)
KENN_FELDER = [
    (r"Kunden-?(?:nummer|nr\.?)|Kd\.?-?Nr\.?|Kunden-?ID", None),
    (r"Patienten-?(?:nummer|nr\.?|ID)", None),
    (r"Vertrags-?(?:nummer|nr\.?)|Versicherungsschein-?(?:nummer|nr\.?)|Policen-?nummer", None),
    (r"Steuer-?(?:ID|IdNr\.?|identifikationsnummer)|Steueridentifikationsnummer|Identifikationsnummer|IdNr\.?", "steuer"),
    (r"Steuer-?(?:nummer|nr\.?)|St\.?-?Nr\.?", None),
    (r"(?:Renten|Sozial)versicherungs-?(?:nummer|nr\.?)|[RS]V-?(?:Nummer|Nr\.?)", "rv"),
    (r"Krankenversicherten-?(?:nummer|nr\.?)|KV-?(?:Nummer|Nr\.?)|Versicherten-?(?:nummer|nr\.?)", "kv"),
    (r"Versicherungs-?(?:nummer|nr\.?)|Vers\.?-?Nr\.?", None),
    (r"(?:Personal)?ausweis-?(?:nummer|nr\.?)|Ausweis-?Nr\.?", "ausweis"),
    (r"(?:Reise)?pass-?(?:nummer|nr\.?)", None),
    (r"F\u00fchrerschein-?(?:nummer|nr\.?)", None),
    (r"Konto-?(?:nummer|nr\.?)|Kto\.?-?Nr\.?", None),
    (r"(?:Kredit)?karten-?(?:nummer|nr\.?)", "karte"),
    (r"BIC|SWIFT(?:-Code)?", "bic"),
    (r"(?:amtl\.?\s+|Kfz-?|amtliches\s+)?Kennzeichen", None),
    (r"IP-?Adresse", None),
]
_KENN_WERT = r"([A-Z\u00c4\u00d6\u00dc0-9]+(?![a-z\u00e4\u00f6\u00fc\u00df])(?:[ \-./][A-Z\u00c4\u00d6\u00dc0-9]+(?![a-z\u00e4\u00f6\u00fc\u00df])){0,6})"
KENN_MUSTER = [(re.compile(rf"(?<![\w-])(?i:{feld})[ \t]*(?::|#|Nr\.?)?[ \t]*{_KENN_WERT}"), pz)
               for feld, pz in KENN_FELDER]
# Formate, die auch ohne Feldbezeichnung gesucht werden (nur mit gültiger Prüfziffer)
FORMAT_MUSTER = [
    ("steuer", "FORMAT_STEUER", re.compile(r"(?<![\d.,/])[1-9]\d[ ]?\d{3}[ ]?\d{3}[ ]?\d{3}(?![\d.,/])")),
    ("rv", "FORMAT_RV", re.compile(r"(?<![\w])\d{2}[ ]?\d{6}[ ]?[A-Z][ ]?\d{2}[ ]?\d(?![\w])")),
    ("kv", "FORMAT_KV", re.compile(r"(?<![\w])[A-Z]\d{9}(?![\w])")),
    ("karte", "FORMAT_KARTE", re.compile(r"(?<![\d])[3-6]\d{3}(?:[ \-]?\d{4}){2}[ \-]?\d{1,7}(?![\d])")),
    ("ip", "FORMAT_IP", re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?![\d.])")),
]


def _quersumme(n: int) -> int:
    return sum(int(c) for c in str(n))


def _pz_steuer(s: str) -> bool:
    """Steuer-ID: 11 Ziffern, erste nicht 0, Prüfziffer nach ISO 7064 (Mod 11,10)."""
    z = re.sub(r"\D", "", s.translate(_OCR_ZIFFER))
    if len(z) != 11 or z[0] == "0":
        return False
    produkt = 10
    for c in z[:10]:
        summe = (int(c) + produkt) % 10 or 10
        produkt = (summe * 2) % 11
    return (11 - produkt) % 10 == int(z[10])


def _pz_rv(s: str) -> bool:
    """Rentenversicherungsnummer: Bereich (2), Geburtsdatum TTMMJJ, Buchstabe, Seriennummer (2),
    Prüfziffer. Buchstabe als Position im Alphabet, Gewichte 2-1-2-5-7-1-2-1-2-1-2-1."""
    z = re.sub(r"\s", "", s).upper()
    m = re.fullmatch(r"(\d{2})(\d{2})(\d{2})(\d{2})([A-Z])(\d{2})(\d)", z)
    if not m or not (1 <= int(m.group(2)) % 50 <= 31 and 1 <= int(m.group(3)) <= 12):
        return False
    ziffern = m.group(1) + m.group(2) + m.group(3) + m.group(4) + f"{ord(m.group(5)) - 64:02d}" + m.group(6)
    gewichte = [2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1]
    return sum(_quersumme(int(c) * g) for c, g in zip(ziffern, gewichte)) % 10 == int(m.group(7))


def _pz_kv(s: str) -> bool:
    """Krankenversichertennummer: Buchstabe + 9 Ziffern; Buchstabe als zweistellige Zahl,
    mit den ersten 8 Ziffern abwechselnd 1 und 2 gewichtet, Quersummen addiert, Mod 10."""
    z = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[A-Z]\d{9}", z):
        return False
    ziffern = f"{ord(z[0]) - 64:02d}" + z[1:9]
    return sum(_quersumme(int(c) * (1 if i % 2 == 0 else 2)) for i, c in enumerate(ziffern)) % 10 == int(z[9])


def _pz_ausweis(s: str) -> bool:
    """Personalausweis-Seriennummer mit Prüfziffer: 9 Zeichen + Ziffer, Gewichte 7-3-1."""
    z = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[0-9A-Z]{9}\d", z):
        return False
    werte = [int(c, 36) for c in z[:9]]
    return sum(w * (7, 3, 1)[i % 3] for i, w in enumerate(werte)) % 10 == int(z[9])


def _pz_karte(s: str) -> bool:
    """Kreditkartennummer: 13 bis 19 Ziffern, Luhn-Prüfung."""
    z = re.sub(r"\D", "", s)
    if not 13 <= len(z) <= 19:
        return False
    summe = 0
    for i, c in enumerate(reversed(z)):
        d = int(c) * (2 if i % 2 else 1)
        summe += d - 9 if d > 9 else d
    return summe % 10 == 0


PRUEFZIFFER = {"steuer": _pz_steuer, "rv": _pz_rv, "kv": _pz_kv, "ausweis": _pz_ausweis,
               "karte": _pz_karte, "ip": lambda s: True}
# Nur Formatprüfung, keine Prüfziffer: BIC (Bank, Land, Ort, optional Filiale)
FORMAT_OHNE_PZ = {"bic": lambda s: bool(re.fullmatch(r"[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?", s.replace(" ", "")))}

# --- Geburtsdatum (nur mit Kontext; alle anderen Daten bleiben lesbar, Nutzer 2026-11-12) ---
_MONATE = "Januar|Februar|M\u00e4rz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
GEB_MUSTER = re.compile(
    rf"(?<!\w)(?i:geb\.|geboren(?:[ \t]+am)?|Geburtsdatum|Geb\.-?Datum|Geburtstag)[ \t]*:?[ \t]*"
    rf"(\d{{1,2}}\.[ \t]?\d{{1,2}}\.[ \t]?(?:\d{{4}}|\d{{2}})(?!\d)|\d{{1,2}}\.[ \t]?(?:{_MONATE})[ \t]+\d{{4}})")
GEBURTSORT_MUSTER = re.compile(rf"(?<!\w)(?i:Geburtsort)[ \t]*:[ \t]*({GROSS}(?:[ \t\-]{GROSS})?)")

# --- Gesundheitsdaten (Art. 9 DSGVO): Diagnosen, Krankheiten, Medikamente, Behandlungen,
# Behinderungen (Nutzer 2026-11-12). Alter und Datum werden nicht erkannt. ---
GES_FELD_MUSTER = re.compile(
    r"(?<!\w)(?i:Diagnosen?|Befunde?|Erkrankungen?|Krankheit(?:en)?|Vorerkrankungen?|Krankheitsbild|"
    r"Medikation|Medikamente?|Behandlungen?|Therapien?|Behinderungen?|Grad der Behinderung|GdB|"
    r"Pflegegrad|Allergien?)[ \t]*:[ \t]*([^\n]{2,120}?)[ \t]*(?=\.[ \t]+[A-Z\u00c4\u00d6\u00dc]|\.?[ \t]*$)",
    re.MULTILINE)
GES_KONTEXT_MUSTER = [
    re.compile(r"(?<!\w)(?:leidet|leiden|litt|erkrankt(?:e|en)?)[ \t]+(?:seit[ \t]+[^\s,.;]+(?:[ \t]+[^\s,.;]+)?[ \t]+)?"
               r"(?:an|unter)[ \t]+(?:(?:einer|einem|einen|eine|chronischer|chronischen|akuter|akuten)[ \t]+)*"
               r"([^.,;:\n]{3,60})"),
    re.compile(r"(?<!\w)wegen[ \t]+(?:(?:einer|eines|einem)[ \t]+)?([^.,;:\n]{3,50}?)[ \t]+in[ \t]+"
               r"(?:(?:\u00e4rztlicher|station\u00e4rer|ambulanter|psychiatrischer|psychotherapeutischer)[ \t]+)?Behandlung"),
    re.compile(r"(?<!\w)(?:wurde|wurden)[ \t]+(?:bei[ \t]+\S+[ \t]+)?(?:(?:eine|ein|einen)[ \t]+)?"
               r"([^.,;:\n]{3,50}?)[ \t]+(?:diagnostiziert|festgestellt)"),
]
GES_WOERTER = [
    r"Diabetes(?:[ \t]+mellitus)?(?:[ \t]+Typ[ \t]+[12])?", r"Depressionen?", r"depressive[nr]?[ \t]+Episode",
    "Burn-?out", r"Krebserkrankung", r"Karzinom", r"Leuk\u00e4mie", r"Lymphom", r"Demenz", r"Alzheimer(?:-Krankheit)?",
    r"Parkinson(?:-Krankheit)?", r"Multiple[ \t]+Sklerose", r"Epilepsie", r"Asthma(?:[ \t]+bronchiale)?", "COPD",
    "HIV", "AIDS", r"Hepatitis(?:[ \t]+[A-E])?", r"Schlaganfall", r"Herzinfarkt", r"Hypertonie", r"Bluthochdruck",
    r"Schizophrenie", r"Psychose", r"bipolare[nr]?[ \t]+St\u00f6rung", r"Angstst\u00f6rung(?:en)?",
    r"Posttraumatische[nr]?[ \t]+Belastungsst\u00f6rung", "PTBS", r"Essst\u00f6rung", r"Anorexie", r"Bulimie",
    r"Alkoholabh\u00e4ngigkeit", r"Drogenabh\u00e4ngigkeit", r"Suchterkrankung", "ADHS", r"Autismus",
    r"Long[ \t\-]Covid", r"Rheuma(?:toide[ \t]+Arthritis)?", r"Arthrose", r"Bandscheibenvorfall", r"Tinnitus",
    r"Schwerbehinderung", r"schwerbehindert(?:e[nr]?)?", r"Gehörlosigkeit", r"geh\u00f6rlos", r"Blindheit",
    r"Querschnittsl\u00e4hmung", r"Rollstuhl", r"Pflegegrad[ \t]+[1-5]", r"GdB[ \t]+(?:von[ \t]+)?\d{2,3}",
    r"Grad[ \t]+der[ \t]+Behinderung[ \t]+(?:von[ \t]+)?\d{2,3}",
    # Medikamente (häufige Wirkstoffe und Handelsnamen)
    "Insulin", "Metformin", "Ramipril", "Bisoprolol", "Metoprolol", "Amlodipin", "Simvastatin", "Levothyroxin",
    "L-Thyroxin", "Methylphenidat", "Ritalin", "Sertralin", "Citalopram", "Escitalopram", "Fluoxetin", "Venlafaxin",
    "Mirtazapin", "Amitriptylin", "Lithium", "Quetiapin", "Olanzapin", "Risperidon", "Diazepam", "Lorazepam",
    "Methadon", "Tilidin", "Tramadol", "Morphin", "Fentanyl", "Marcumar", "Xarelto", "Eliquis", "Cortison",
    "Prednisolon", "Antidepressiv(?:um|a)", "Neuroleptik(?:um|a)", "Chemotherapie", "Dialyse", "Psychotherapie",
]
GES_WORT_MUSTER = re.compile(r"(?<![\w-])(?:" + "|".join(GES_WOERTER) + r")(?![\w])")
ICD_MUSTER = re.compile(r"(?<!\w)ICD(?:-10)?(?:-GM)?[ \t]*:?[ \t]*([A-TV-Z]\d{2}(?:\.\d{1,2})?[GVAZ]?)(?![\w])")
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


def _iban_pruefziffer_ok(s: str) -> bool:
    """Prüfziffer nach ISO 13616 (Modulo 97), nach Ersatz typischer OCR-Verwechslungen."""
    z = re.sub(r"\s+", "", s)
    n = (z[:2] + z[2:].translate(_OCR_ZIFFER)).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", n):
        return False
    umgestellt = n[4:] + n[:4]
    return int("".join(str(int(c, 36)) for c in umgestellt)) % 97 == 1


def begruendung(fund: Fund) -> list[str]:
    """Lesbare Gründe, warum die Stelle gefunden wurde."""
    return [BEGRUENDUNG.get(q, q) for q in fund.quellen]


def ist_eindeutig(fund: Fund) -> bool:
    """Eindeutig: eine für sich sichere Quelle oder zwei verschiedene Quellen.
    Sonst gehört die Stelle in „zu prüfen“."""
    return bool(EINDEUTIG & set(fund.quellen)) or len(set(fund.quellen)) >= 2


# --- Begriffe tolerant suchen (Texterkennung verwechselt Zeichen) ---------------
_OCR_GLEICH = str.maketrans({"0": "o", "1": "l", "i": "l", "|": "l", "!": "l", "5": "s", "8": "b", "6": "b"})


def _ocr_form(s: str) -> str:
    """Vergleichsform für Texterkennung: klein, ohne Satzzeichen, Verwechslungen vereinheitlicht."""
    return re.sub(r"[\W_]", "", s.lower()).translate(_OCR_GLEICH)


def _abstand(a: str, b: str) -> int:
    """Levenshtein-Abstand (Einfügen, Löschen, Ersetzen je 1)."""
    vorher = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        jetzt = [i]
        for j, cb in enumerate(b, 1):
            jetzt.append(min(vorher[j] + 1, jetzt[j - 1] + 1, vorher[j - 1] + (ca != cb)))
        vorher = jetzt
    return vorher[-1]


def begriff_treffer(text: str, woerter: list[Wort], begriff: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Fundstellen eines Begriffs: (genau, ähnlich). Ähnlich nur bei Wörtern aus der
    Texterkennung: typische Verwechslungen gleich, dazu ein abweichendes Zeichen ab
    5 Buchstaben, zwei ab 10. Mehrteilige Begriffe dürfen als ein Wort erkannt sein."""
    begriff = begriff.strip()
    genau = [(m.start(), m.end()) for m in
             re.finditer(r"(?<!\w)" + re.escape(begriff) + r"(?!\w)", text, re.IGNORECASE)]
    ziel = _ocr_form(begriff)
    if len(ziel) < 3:
        return genau, []
    erlaubt = 2 if len(ziel) >= 10 else 1 if len(ziel) >= 5 else 0
    aehnlich = []
    for anzahl in sorted({len(begriff.split()), 1}):
        for i in range(len(woerter) - anzahl + 1):
            gruppe = woerter[i:i + anzahl]
            if not all(w.ocr for w in gruppe) or "\n" in text[gruppe[0].start:gruppe[-1].ende]:
                continue
            kandidat = _ocr_form("".join(w.text for w in gruppe))
            if abs(len(kandidat) - len(ziel)) > erlaubt or _abstand(kandidat, ziel) > erlaubt:
                continue
            s, e = gruppe[0].start, gruppe[-1].ende
            if not any(gs < e and ge > s for gs, ge in genau + aehnlich):
                aehnlich.append((s, e))
    return genau, aehnlich


# --- Formularzeilen auf Scans ------------------------------------------------------
# Feldbezeichnung am Zeilenanfang -> Art der Einträge rechts daneben. Handschrift liest die
# Texterkennung oft falsch, ihre Wortpositionen stimmen aber meist. „Ort/Datum“ fehlt
# absichtlich: Daten bleiben lesbar (Nutzer 2026-11-12).
FORMULAR_LABEL = re.compile(
    r"(?i:(Herr\s*/\s*Fr\w*|Herrn?|Frau|Name|Vorname|Nachname|Familienname|Geburtsname)"
    r"|(geboren\s+am|Geburtsdatum|geb\.)|(Geburtsort)|(Anschrift|Wohnort|wohnhaft|Stra(?:ß|ss)e))[ \t]*:?")
FORMULAR_ARTEN = {1: "PER", 2: "GEB", 3: "ORT", 4: "ADR"}


def formularzeilen(text: str, woerter: list[Wort]) -> list[tuple[int, int, str, str]]:
    """Spans der Wörter rechts neben einer Feldbezeichnung (nur Texterkennung). Geometrisch:
    gleiche Höhe wie die Bezeichnung (mit Spielraum für größere Handschrift), höchstens 6 Wörter."""
    spans = []
    for m in FORMULAR_LABEL.finditer(text):
        zeilenanfang = text.rfind("\n", 0, m.start()) + 1
        if text[zeilenanfang:m.start()].strip():
            continue
        label = [i for i, w in enumerate(woerter) if w.start < m.end() and w.ende > m.start()]
        if not label or not all(woerter[i].ocr for i in label):
            continue
        y0 = min(woerter[i].rect[1] for i in label)
        y1 = max(woerter[i].rect[3] for i in label)
        x1 = max(woerter[i].rect[2] for i in label)
        h = y1 - y0
        # Rest des Label-Worts (z. B. „Herr/Frau“ als ein Wort) zählt nicht als Eintrag
        kandidaten = sorted(
            (j for j, w in enumerate(woerter)
             if j not in label and w.ocr and w.rect[0] >= x1 - 1
             and y0 - 0.7 * h <= (w.rect[1] + w.rect[3]) / 2 <= y1 + 0.7 * h),
            key=lambda j: woerter[j].rect[0])
        gewaehlt = []
        for j in kandidaten:
            if FORMULAR_LABEL.fullmatch(woerter[j].text.strip()) or len(gewaehlt) == 6:
                break
            gewaehlt.append(j)
        art = FORMULAR_ARTEN[m.lastindex]
        for lauf in _laeufe(sorted(gewaehlt)):
            spans.append((woerter[lauf[0]].start, woerter[lauf[-1]].ende, art, "FORMULARZEILE"))
    return spans


def _laeufe(indizes: list[int]) -> list[list[int]]:
    """Teilt sortierte Wortindizes in Folgen aufeinanderfolgender Indizes."""
    laeufe: list[list[int]] = []
    for i in indizes:
        if laeufe and i == laeufe[-1][-1] + 1:
            laeufe[-1].append(i)
        else:
            laeufe.append([i])
    return laeufe


# --- Markieren von Hand ---------------------------------------------------------------

def wort_an_punkt(woerter: list[Wort], x: float, y: float, toleranz: float = 2.0) -> int | None:
    """Index des Wortes unter dem Punkt (PDF-Punkte); bei mehreren das kleinste."""
    flaeche = [(w.rect[2] - w.rect[0]) * (w.rect[3] - w.rect[1]) for w in woerter]
    beste = None
    for i, w in enumerate(woerter):
        x0, y0, x1, y1 = w.rect
        if x0 - toleranz <= x <= x1 + toleranz and y0 - toleranz <= y <= y1 + toleranz:
            if beste is None or flaeche[i] < flaeche[beste]:
                beste = i
    return beste


def woerter_im_bereich(woerter: list[Wort], rect: tuple[float, float, float, float]) -> list[int]:
    """Wörter, deren Mittelpunkt im Rechteck liegt (für Markdown und Anzeige)."""
    x0, y0, x1, y1 = rect
    return [i for i, w in enumerate(woerter)
            if x0 <= (w.rect[0] + w.rect[2]) / 2 <= x1 and y0 <= (w.rect[1] + w.rect[3]) / 2 <= y1]


def finde(text: str, woerter: list[Wort], nlp, vornamen: set[str], gelernt: list[str],
          begriffe: list[str] = ()) -> list[Fund]:
    spans: list[tuple[int, int, str, str]] = []   # Anfang, Ende, Art, Quelle

    if nlp is not None:
        for ent in nlp(text).ents:
            art = SPACY_ARTEN.get(ent.label_)
            if not art:
                continue
            # Fundstellen nie über Zeilenumbrüche ziehen (sonst z. B.
            # Absender und Anschrift als eine Stelle)
            pos = ent.start_char
            for teil in text[ent.start_char:ent.end_char].split("\n"):
                spans.append((pos, pos + len(teil), art, f"MODELL_{art}"))
                pos += len(teil) + 1

    for (art, rx), quelle_muster in zip(MUSTER, MUSTER_QUELLEN):
        for m in rx.finditer(text):
            quelle = quelle_muster
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
            if art == "IBAN":
                if not _ist_iban(m.group(0)):
                    continue
                if not _iban_pruefziffer_ok(m.group(0)):
                    quelle = "IBAN_UNSICHER"
            if art == "TEL" and (_ist_datum(m.group(0)) or sum(c.isdigit() for c in m.group(0)) < 6):
                continue
            spans.append((s, e, art, quelle))

    # E-Mail-Adressen nach Texterkennung: Wort mit "@" immer ganz erfassen; fehlt der
    # Punkt vor der Endung ("example org"), die Endung als Folgewort anhängen
    for i, w in enumerate(woerter):
        if "@" in w.text and not rx_mail.fullmatch(w.text.strip(".,;:")):
            ende = w.ende
            if "." not in w.text.split("@", 1)[1].strip(".,;:") and i + 1 < len(woerter) \
                    and re.fullmatch(r"[a-z]{2,4}[.,;:]?", woerter[i + 1].text) \
                    and text[w.ende:woerter[i + 1].start].strip() == "":
                ende = woerter[i + 1].ende
            spans.append((w.start, ende, "MAIL", "MAIL_OCR"))

    # Vornamenliste: Vorname + folgendes großgeschriebenes Wort
    for i, w in enumerate(woerter):
        if w.text.strip(".,;:").lower() in vornamen:
            ende = w.ende
            if i + 1 < len(woerter) and re.fullmatch(GROSS + r"[.,;:]?", woerter[i + 1].text) \
                    and text[w.ende:woerter[i + 1].start].strip() == "":
                ende = woerter[i + 1].ende
            spans.append((w.start, ende, "PER", "VORNAME"))

    # Begriffe zum Schwärzen nur für dieses Dokument und gelernte Begriffe, auf Scans auch ähnlich
    for liste, art, q_genau, q_aehnlich in ((begriffe, "HAND", "BEGRIFF", "BEGRIFF_OCR"),
                                           (gelernt, "LISTE", "LISTE", "LISTE_OCR")):
        for begriff in liste:
            if len(begriff.strip()) < 2:
                continue
            genau, aehnlich = begriff_treffer(text, woerter, begriff)
            spans += [(s_, e_, art, q_aehnlich) for s_, e_ in aehnlich]
            if art == "HAND":   # gelernte Begriffe: genaue Treffer folgen unten wie bisher
                spans += [(s_, e_, art, q_genau) for s_, e_ in genau]

    # Formularzeilen auf Scans (Handschrift neben gedruckter Feldbezeichnung)
    spans += formularzeilen(text, woerter)

    # Gelernte Begriffe (Blacklist)
    for begriff in gelernt:
        if len(begriff.strip()) < 2:
            continue
        for m in re.finditer(r"(?<!\w)" + re.escape(begriff.strip()) + r"(?!\w)", text, re.IGNORECASE):
            spans.append((m.start(), m.end(), "LISTE", "LISTE"))

    # Kennnummern nach Feldbezeichnung; mit Prüfziffer, wo eine bekannt ist
    for rx, pz in KENN_MUSTER:
        for m in rx.finditer(text):
            wert = m.group(1)
            if pz in FORMAT_OHNE_PZ:
                if not FORMAT_OHNE_PZ[pz](wert):
                    continue
                quelle = "KENN_FELD"
            elif sum(c.isdigit() for c in wert) < 1 or len(re.sub(r"\W", "", wert)) < 4:
                continue
            elif pz is None:
                quelle = "KENN_FELD"
            else:
                quelle = "KENN_PZ" if PRUEFZIFFER[pz](wert) else "KENN_PZ_FALSCH"
            spans.append((m.start(1), m.end(1), "KENN", quelle))
    # Kennnummern nur am Format erkennbar: nur mit gültiger Prüfziffer, gelten als „zu prüfen“
    for pz, quelle, rx in FORMAT_MUSTER:
        for m in rx.finditer(text):
            if PRUEFZIFFER[pz](m.group(0)):
                spans.append((m.start(), m.end(), "KENN", quelle))

    # Geburtsdatum und Geburtsort nur mit Kontext
    for m in GEB_MUSTER.finditer(text):
        spans.append((m.start(1), m.end(1), "GEB", "GEB"))
    for m in GEBURTSORT_MUSTER.finditer(text):
        spans.append((m.start(1), m.end(1), "ORT", "GEBURTSORT"))

    # Gesundheitsdaten
    for m in GES_FELD_MUSTER.finditer(text):
        spans.append((m.start(1), m.end(1), "GES", "GES_FELD"))
    for rx in GES_KONTEXT_MUSTER:
        for m in rx.finditer(text):
            spans.append((m.start(1), m.end(1), "GES", "GES_KONTEXT"))
    for m in GES_WORT_MUSTER.finditer(text):
        spans.append((m.start(), m.end(), "GES", "GES_WORT"))
    for m in ICD_MUSTER.finditer(text):
        spans.append((m.start(1), m.end(1), "GES", "ICD"))

    # Satzzeichen am Rand abschneiden, überlappende Stellen zusammenfassen
    bereinigt = []
    for s, e, art, quelle in spans:
        while s < e and text[s] in " \t\n.,;:()\"'":
            s += 1
        while e > s and text[e - 1] in " \t\n.,;:()\"'":
            e -= 1
        if art == "PER":   # Anrede und Titel bleiben lesbar
            m = ANREDE.match(text, s, e)
            if m and m.end() < e:
                s = m.end()
        if e > s:
            bereinigt.append((s, e, art, quelle))
    bereinigt.sort()
    zusammen: list[list] = []
    rang = ["HAND", "LISTE", "IBAN", "KENN", "MAIL", "TEL", "GEB", "GES", "PER", "ADR", "ORT", "ORG"]
    for s, e, art, quelle in bereinigt:
        if zusammen and s < zusammen[-1][1]:
            letzte = zusammen[-1]
            letzte[1] = max(letzte[1], e)
            if rang.index(art) < rang.index(letzte[2]):
                letzte[2] = art
            letzte[3].append((quelle, art, s, e))
        else:
            zusammen.append([s, e, art, [(quelle, art, s, e)]])

    funde = []
    for s, e, art, paare in zusammen:
        idx = [i for i, w in enumerate(woerter) if w.start < e and w.ende > s]
        if idx:
            # Als Grund zählt eine Quelle der endgültigen Art oder eine, die die ganze Stelle
            # abdeckt (eine Telefonnummer-Teilfolge in einer IBAN begründet die IBAN nicht)
            quellen = tuple(dict.fromkeys(
                q for q, a, qs, qe in paare if a == art or (qs <= s and qe >= e)))
            funde.append(Fund(text[s:e].replace("\n", " "), art, idx, s, e, quellen))
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
    "MAIL": "E-Mail", "IBAN": "IBAN", "ADR": "Anschrift", "KENN": "Kennnummer",
    "GEB": "Geburtsdatum", "GES": "Gesundheitsangabe", "LISTE": "geschwärzt", "HAND": "geschwärzt",
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


# --- 4. PDF öffnen und schwärzen ------------------------------------------------

def oeffne_pdf(daten: bytes):
    """Öffnet das PDF und übernimmt Formularfelder und Anmerkungen fest in die Seiten.

    apply_redactions() entfernt nur Seiteninhalt. Werte von Formularfeldern
    (z. B. "Name") und Anmerkungen (z. B. Notizen) liegen außerhalb davon und
    blieben sonst lesbar über den Balken stehen.
    """
    import pymupdf
    doc = pymupdf.open(stream=daten, filetype="pdf")
    for page in doc:
        for widget in page.widgets():
            try:
                widget.update()   # Darstellung aus dem Feldwert erzeugen, falls sie fehlt
            except Exception:
                pass
    doc.bake(annots=True, widgets=True)
    return doc


def seitenauswahl(text: str, n: int) -> list[int]:
    """Liest eine Seitenangabe wie „1-3, 5“ (1-basiert) und liefert sortierte
    Seitenindizes (0-basiert). Leer heißt alle Seiten. Fehler -> ValueError."""
    if not text.strip():
        return list(range(n))
    seiten: set[int] = set()
    for teil in text.replace(";", ",").split(","):
        teil = teil.strip().replace("–", "-")
        if not teil:
            continue
        m = re.fullmatch(r"(\d+)\s*(?:-\s*(\d+))?", teil)
        if not m:
            raise ValueError(f"„{teil}“ ist keine Seitenangabe (Beispiel: 1-3, 5).")
        von, bis = int(m.group(1)), int(m.group(2) or m.group(1))
        if von > bis:
            von, bis = bis, von
        if von < 1 or bis > n:
            raise ValueError(f"Seite {von if von < 1 else bis} gibt es nicht (1 bis {n}).")
        seiten.update(range(von - 1, bis))
    if not seiten:
        raise ValueError("Keine Seite angegeben.")
    return sorted(seiten)


def schwaerze(daten: bytes, rechtecke: dict[int, list[tuple]], seiten: list[int] | None = None) -> tuple[bytes, int]:
    """Schwärzt physisch: Text, Bildteile und Vektorgrafik unter den Rechtecken
    werden entfernt, nicht nur überdeckt. Metadaten, XMP, Lesezeichen und
    eingebettete Dateien werden gelöscht.

    rechtecke: Seitenindex -> Rechtecke (PDF-Punkte); jede genannte Seite wird
    bereinigt, auch mit leerer Liste. seiten: nur diese Seiten (0-basiert, sortiert)
    exportieren, None = alle. Liefert (PDF-Daten, Anzahl Rechtecke).
    """
    import pymupdf
    doc = oeffne_pdf(daten)
    anzahl = 0
    for p, liste in rechtecke.items():
        if seiten is not None and p not in seiten:
            continue
        page = doc[p]
        for r in liste:
            page.add_redact_annot(pymupdf.Rect(*r), fill=(0, 0, 0))
            anzahl += 1
        page.apply_redactions()
    if seiten is not None and list(seiten) != list(range(len(doc))):
        doc.select(list(seiten))
    bereinige_pdf(doc)   # Autor, Titel, XMP, Lesezeichen, Anhänge entfernen
    puffer = io.BytesIO()
    doc.save(puffer, garbage=4, deflate=True)
    return puffer.getvalue(), anzahl


# --- 5. Export bereinigen und prüfen --------------------------------------------

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


def pruefe_export(daten: bytes, rechtecke: dict[int, list[tuple[float, float, float, float]]],
                  nummern: list[int] | None = None) -> list[str]:
    """Prüft das fertige PDF und liefert Meldungen (leer = nichts gefunden).

    Die Meldungen nennen nur Art und Seite, nie den geschwärzten Text.
    rechtecke: Seitenindex (0-basiert) -> Rechtecke, die geschwärzt sein müssen.
    nummern: bei Export einzelner Seiten die Originalseite (0-basiert) je Exportseite;
    die Meldungen nennen dann die Seitenzahl im Original.
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
    def seite(p):
        return f"Seite {(nummern[p] if nummern and p < len(nummern) else p) + 1}"
    try:
        for p, liste in sorted(rechtecke.items()):
            if p >= len(doc):
                meldungen.append(f"{seite(p)} fehlt im Export.")
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
                meldungen.append(f"{seite(p)}: {unter_balken} Stelle(n) mit Text unter dem Balken.")
            if hell:
                meldungen.append(f"{seite(p)}: {hell} Balken im Bild nicht vollständig schwarz.")
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


# --- 6. Prüfprotokoll -----------------------------------------------------------

def pruefprotokoll(*, version: str, modell: str, zeitpunkt: str, original: bytes, export: bytes,
                   seiten_gesamt: int, quellen: dict[int, str], funde: dict[int, list],
                   gewaehlt, balken: int, meldungen: list[str], exportiert: list[int] | None = None,
                   von_hand: int = 0) -> str:
    """Prüfprotokoll als Markdown, ohne Originaldaten (kein Dateiname, kein Text der Fundstellen).

    quellen:  Seitenindex -> "Textebene" oder "Texterkennung" (nur gescannte Seiten)
    funde:    Seitenindex -> Liste von Fund (nur gescannte Seiten)
    gewaehlt: Funktion (Seitenindex, Fund) -> bool
    meldungen: Ergebnis von pruefe_export (leer = bestanden)
    exportiert: nur diese Seiten (0-basiert) wurden exportiert, None = alle
    von_hand: Anzahl der in der Vorschau von Hand markierten Wörter und Bereiche
    """
    import hashlib
    seiten = list(range(seiten_gesamt)) if exportiert is None else list(exportiert)
    gescannt = sorted(p for p in quellen if p in seiten)
    offen = [p + 1 for p in seiten if p not in quellen]
    je_art: dict[str, list[int]] = {}
    for p in gescannt:
        for f in funde.get(p, []):
            z = je_art.setdefault(f.art, [0, 0])
            z[0] += 1
            z[1] += 1 if gewaehlt(p, f) else 0
    summe = [sum(z[0] for z in je_art.values()), sum(z[1] for z in je_art.values())]
    nach_quelle: dict[str, list[int]] = {}
    for p in gescannt:
        nach_quelle.setdefault(quellen[p], []).append(p + 1)

    z = ["# Prüfprotokoll Grauzone PRO", "",
         f"Erstellt am {zeitpunkt} mit Grauzone PRO {version}, Erkennungsmodell {modell}.", "",
         "Dieses Protokoll enthält keine Originaldaten: weder Dateiname noch Text der Fundstellen.", "",
         "## Dokument", "",
         f"- Kennung des Originals (SHA-256): `{hashlib.sha256(original).hexdigest()}`",
         f"- Kennung des geschwärzten PDF (SHA-256): `{hashlib.sha256(export).hexdigest()}`",
         f"- Seiten gesamt: {seiten_gesamt}, gescannt und bearbeitet: {len(gescannt)}"]
    if exportiert is not None and len(seiten) < seiten_gesamt:
        z.append(f"- Exportiert wurden nur die Seiten {', '.join(str(p + 1) for p in seiten)} "
                 f"({len(seiten)} von {seiten_gesamt})")
    for q, liste in nach_quelle.items():
        z.append(f"- Gelesen per {q}: Seite {', '.join(map(str, liste))}")
    if offen:
        z.append(f"- **Nicht gescannt und daher nicht geschwärzt: Seite {', '.join(map(str, offen))}**")
    z += ["", "## Fundstellen", "", "| Art | Gefunden | Geschwärzt | Abgewählt |", "|---|---:|---:|---:|"]
    for art in sorted(je_art):
        g, s = je_art[art]
        z.append(f"| {ARTEN.get(art, art)} | {g} | {s} | {g - s} |")
    z.append(f"| **Summe** | **{summe[0]}** | **{summe[1]}** | **{summe[0] - summe[1]}** |")
    z += ["", f"Abgewählt heißt: von der prüfenden Person nicht zur Schwärzung ausgewählt "
              f"({summe[0] - summe[1]} Stelle(n)). Geschwärzte Balken im PDF: {balken}."]
    if von_hand:
        z.append(f"Zusätzlich in der Vorschau von Hand markiert (Wörter und Bereiche): {von_hand}.")
    z += ["",
          "## Exportprüfung", ""]
    if meldungen:
        z += ["Ergebnis: **nicht bestanden**", ""] + [f"- {m}" for m in meldungen]
    else:
        z.append("Ergebnis: **bestanden**")
    z += ["", "Geprüft am fertigen PDF: Text und Helligkeit unter jedem Balken, Dokumenteigenschaften, "
              "XMP-Metadaten, Lesezeichen, eingebettete Dateien, Anmerkungen, Formularfelder. "
              "Das Markdown wird aus denselben Fundstellen erzeugt und nicht gesondert geprüft.", "",
          "## Hinweise", "",
          "- Die automatische Erkennung ist nicht vollständig. Das Ergebnis ersetzt keine Prüfung durch eine Person.",
          "- Dieses Protokoll begründet keine Revisionssicherheit und keine rechtliche Bewertung.", ""]
    return "\n".join(z)
