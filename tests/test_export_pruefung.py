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


if __name__ == "__main__":
    unittest.main()
