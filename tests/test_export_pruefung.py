"""Tests für Bereinigung und Prüfung des Exports (erfundene Daten, ohne Oberfläche).

Aufruf im Projektordner: ./venv/bin/python -m unittest discover -s tests
"""
import os
import sys
import unittest

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import erkennung as E

XMP = ("<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
       "<rdf:Description xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:creator>Erika Mustermann</dc:creator>"
       "</rdf:Description></rdf:RDF></x:xmpmeta>")


def testdokument(scan: bool = False):
    """PDF mit Name im Text, in Dokumenteigenschaften, XMP, Lesezeichen und Anhang."""
    doc = pymupdf.open()
    seite = doc.new_page()
    seite.insert_text((60, 80), "Erika Mustermann wohnt in Musterstadt", fontsize=14)
    if scan:   # Bild der Seite mit unsichtbarer Textebene darüber (durchsuchbarer Scan)
        bild = seite.get_pixmap(dpi=150)
        doc = pymupdf.open()
        seite = doc.new_page()
        seite.insert_image(seite.rect, pixmap=bild)
        seite.insert_text((60, 80), "Erika Mustermann wohnt in Musterstadt", fontsize=14, render_mode=3)
    doc.set_metadata({"author": "Erika Mustermann", "title": "Akte Mustermann"})
    doc.set_xml_metadata(XMP)
    doc.set_toc([[1, "Erika Mustermann", 1]])
    doc.embfile_add("notiz.txt", b"Erika Mustermann, Privatadresse")
    return doc


def schwaerze(doc, bereinigen: bool):
    seite = doc[0]
    rechtecke = [tuple(r) for r in seite.search_for("Erika Mustermann")]
    for r in rechtecke:
        seite.add_redact_annot(pymupdf.Rect(*r), fill=(0, 0, 0))
    seite.apply_redactions()
    if bereinigen:
        E.bereinige_pdf(doc)
    else:
        doc.set_metadata({})   # Stand von 0.4.6
    return doc.tobytes(garbage=4, deflate=True), {0: rechtecke}


class ExportPruefung(unittest.TestCase):
    def test_ohne_bereinigung_werden_reste_gemeldet(self):
        daten, rechtecke = schwaerze(testdokument(), bereinigen=False)
        meldungen = " ".join(E.pruefe_export(daten, rechtecke))
        self.assertIn("XMP", meldungen)
        self.assertIn("Lesezeichen", meldungen)
        self.assertIn("Eingebettete Dateien", meldungen)

    def test_mit_bereinigung_ist_der_export_sauber(self):
        for scan in (False, True):
            with self.subTest(scan=scan):
                daten, rechtecke = schwaerze(testdokument(scan), bereinigen=True)
                self.assertEqual(E.pruefe_export(daten, rechtecke), [])
                neu = pymupdf.open(stream=daten, filetype="pdf")
                self.assertNotIn("Mustermann", neu[0].get_text())
                self.assertEqual(neu.get_xml_metadata().strip(), "")
                self.assertEqual(neu.get_toc(), [])
                self.assertEqual(neu.embfile_names(), [])

    def test_fehlende_schwaerzung_wird_erkannt(self):
        doc = testdokument()
        rechtecke = {0: [tuple(r) for r in doc[0].search_for("Erika Mustermann")]}
        E.bereinige_pdf(doc)
        meldungen = E.pruefe_export(doc.tobytes(), rechtecke)   # nicht geschwärzt
        self.assertTrue(any("Text unter dem Balken" in m for m in meldungen))
        self.assertTrue(any("nicht vollständig schwarz" in m for m in meldungen))

    def test_meldungen_enthalten_keinen_geschwaerzten_text(self):
        doc = testdokument()
        rechtecke = {0: [tuple(r) for r in doc[0].search_for("Erika Mustermann")]}
        meldungen = " ".join(E.pruefe_export(doc.tobytes(), rechtecke))
        self.assertNotIn("Mustermann", meldungen)


class Pruefprotokoll(unittest.TestCase):
    def protokoll(self, meldungen=(), gewaehlt=lambda p, f: True):
        funde = {0: [E.Fund("Erika Mustermann", "PER"), E.Fund("0221 123456", "TEL")],
                 1: [E.Fund("Erika Mustermann", "PER")]}
        return E.pruefprotokoll(
            version="0.0.0-test", modell="core_news_test", zeitpunkt="01.01.2026 12:00",
            original=b"original", export=b"export", seiten_gesamt=3,
            quellen={0: "Textebene", 1: "Texterkennung"}, funde=funde, gewaehlt=gewaehlt,
            balken=3, meldungen=list(meldungen))

    def test_zahlen_und_kennungen(self):
        text = self.protokoll(gewaehlt=lambda p, f: f.art != "TEL")
        self.assertIn("| Person | 2 | 2 | 0 |", text)
        self.assertIn("| Telefon | 1 | 0 | 1 |", text)
        self.assertIn("| **Summe** | **3** | **2** | **1** |", text)
        import hashlib
        self.assertIn(hashlib.sha256(b"original").hexdigest(), text)
        self.assertIn(hashlib.sha256(b"export").hexdigest(), text)
        self.assertIn("Nicht gescannt und daher nicht geschwärzt: Seite 3", text)
        self.assertIn("Ergebnis: **bestanden**", text)

    def test_kein_originaltext(self):
        text = self.protokoll()
        for verboten in ("Mustermann", "0221", "123456"):
            self.assertNotIn(verboten, text)

    def test_meldungen_stehen_im_protokoll(self):
        text = self.protokoll(meldungen=["XMP-Metadaten nicht leer."])
        self.assertIn("nicht bestanden", text)
        self.assertIn("XMP-Metadaten nicht leer.", text)


if __name__ == "__main__":
    unittest.main()
