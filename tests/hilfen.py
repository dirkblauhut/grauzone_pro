"""Gemeinsame Hilfen für die Tests: erzeugen PDFs mit erfundenen Daten und
bilden den Ablauf aus app.py (scanne, funde_der_seite, Export) ohne Streamlit nach."""
import os
import sys

import pymupdf

PROJEKT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJEKT)

import erkennung as E  # noqa: E402

_NLP = None


def nlp():
    """Kleines deutsches spaCy-Modell (schneller als lg); None, wenn keins installiert ist."""
    global _NLP
    if _NLP is None:
        import spacy
        for name in ("de_core_news_sm", "de_core_news_lg"):
            try:
                _NLP = spacy.load(name)
                break
            except OSError:
                continue
    return _NLP


def text_seite(doc, zeilen, y=72):
    """Neue A4-Seite mit Textebene; jede Zeile 18 pt tiefer."""
    page = doc.new_page(width=595, height=842)
    for i, zeile in enumerate(zeilen):
        page.insert_text((72, y + i * 18), zeile, fontsize=11, fontname="helv")
    return page


def bild_seite(doc, zeilen):
    """Neue Seite, die die Zeilen nur als Bild enthält (wie ein Scan, ohne Textebene)."""
    vorlage = pymupdf.open()
    text_seite(vorlage, zeilen)
    pix = vorlage[0].get_pixmap(matrix=pymupdf.Matrix(3, 3))
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, pixmap=pix)
    return page


def formular_seite(doc, feldname, wert):
    """Neue Seite mit einem ausgefüllten Textfeld und einer Beschriftung."""
    page = text_seite(doc, ["Antrag auf Musterleistung"])
    feld = pymupdf.Widget()
    feld.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    feld.field_name = feldname
    feld.field_value = wert
    feld.rect = pymupdf.Rect(72, 120, 372, 140)
    page.add_widget(feld)
    return page


def als_bytes(doc):
    return doc.tobytes()


def scanne(daten, ocr_reader=None, vornamen=frozenset(), gelernt=()):
    """Wie app.py: Textebene, bei weniger als drei Wörtern Texterkennung.
    Liefert je Seite (text, woerter, funde, quelle)."""
    doc = E.oeffne_pdf(daten)
    seiten = []
    for page in doc:
        zeilen = E.woerter_aus_textebene(page)
        quelle = "Textebene"
        if sum(len(z) for z in zeilen) < 3:
            if ocr_reader is None:
                seiten.append(("", [], [], "fehlt"))
                continue
            zeilen = E.woerter_aus_ocr(ocr_reader, page)
            quelle = "Texterkennung"
        text, woerter = E.seitentext(zeilen)
        funde = E.finde(text, woerter, nlp(), set(vornamen), list(gelernt))
        seiten.append((text, woerter, funde, quelle))
    return seiten


def exportiere(daten, seiten, gewaehlt=lambda p, f: True):
    """Wie der Export in app.py: alle gewählten Fundstellen aller gescannten Seiten schwärzen."""
    rechtecke = {}
    for p, (_text, woerter, funde, quelle) in enumerate(seiten):
        if quelle == "fehlt":
            continue
        rechtecke[p] = [E.wort_rechteck(woerter[i], f) for f in funde if gewaehlt(p, f) for i in f.woerter]
    return E.schwaerze(daten, rechtecke)
