"""Ganzer Ablauf mit echten PDFs: scannen, finden, schwärzen, Ergebnis prüfen.
Prüft vor allem, dass geschwärzter Text wirklich aus der Datei entfernt ist."""
import os
import unittest

import pymupdf

from hilfen import E, als_bytes, bild_seite, exportiere, formular_seite, scanne, text_seite

GEHEIM = ["Mustermann", "0221 1234567", "erika.mustermann@example.org", "Musterweg"]


def mehrseitig():
    doc = pymupdf.open()
    text_seite(doc, ["Sehr geehrte Frau Erika Mustermann,",
                     "bitte rufen Sie uns unter 0221 1234567 an.",
                     "Mit freundlichen Gruessen"])
    text_seite(doc, ["Dieses Blatt enthaelt keine personenbezogenen Daten."])
    text_seite(doc, ["Absender: Frau Erika Mustermann",
                     "Musterweg 12",
                     "12345 Musterstadt",
                     "Mail: erika.mustermann@example.org"])
    doc.set_metadata({"author": "Erika Mustermann", "title": "Antrag Mustermann"})
    return als_bytes(doc)


class Textebene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daten = mehrseitig()
        cls.seiten = scanne(cls.daten)
        cls.ergebnis, cls.anzahl = exportiere(cls.daten, cls.seiten)
        cls.doc = pymupdf.open(stream=cls.ergebnis, filetype="pdf")

    def test_alle_seiten_per_textebene(self):
        self.assertEqual(["Textebene"] * 3, [s[3] for s in self.seiten])

    def test_fundstellen_gefunden(self):
        self.assertGreater(self.anzahl, 0)
        self.assertEqual([], self.seiten[1][2], "Seite 2 hat keine Fundstellen")

    def test_geschwaerzter_text_ist_entfernt(self):
        gesamt = "".join(page.get_text() for page in self.doc)
        for geheim in GEHEIM:
            self.assertNotIn(geheim, gesamt)

    def test_uebriger_text_bleibt(self):
        s1 = self.doc[0].get_text()
        self.assertIn("Sehr geehrte Frau", s1)
        self.assertIn("bitte rufen Sie uns unter", s1)
        self.assertIn("keine personenbezogenen Daten", self.doc[1].get_text())

    def test_metadaten_geloescht(self):
        self.assertFalse(any((self.doc.metadata or {}).get(k) for k in ("author", "title")))
        self.assertNotIn(b"Mustermann", self.ergebnis)

    def test_abgewaehlte_stelle_bleibt(self):
        ergebnis, _ = exportiere(self.daten, self.seiten,
                                 gewaehlt=lambda p, f: f.art != "TEL")
        text = pymupdf.open(stream=ergebnis, filetype="pdf")[0].get_text()
        self.assertIn("0221 1234567", text)
        self.assertNotIn("Mustermann", text)

    def test_nicht_gescannte_seite_bleibt_unveraendert(self):
        # Nur Seite 1 schwärzen; Seite 3 wurde "nicht gescannt"
        seiten = list(self.seiten)
        seiten[2] = ("", [], [], "fehlt")
        ergebnis, _ = exportiere(self.daten, seiten)
        doc = pymupdf.open(stream=ergebnis, filetype="pdf")
        self.assertNotIn("Mustermann", doc[0].get_text())
        self.assertIn("Mustermann", doc[2].get_text())


class Formular(unittest.TestCase):
    def test_formularwert_wird_entfernt(self):
        # Behoben (0.3.1): Wert im Formularfeld blieb nach dem Export lesbar
        doc = pymupdf.open()
        formular_seite(doc, "name", "Frau Erika Mustermann")
        daten = als_bytes(doc)
        seiten = scanne(daten)
        self.assertIn("Mustermann", seiten[0][0], "Feldwert gehört zum Seitentext")
        ergebnis, _ = exportiere(daten, seiten)
        out = pymupdf.open(stream=ergebnis, filetype="pdf")
        self.assertEqual([], list(out[0].widgets()))
        self.assertNotIn("Mustermann", out[0].get_text())
        self.assertNotIn(b"Mustermann", ergebnis)


@unittest.skipUnless(os.environ.get("GRAUZONE_OCR_TEST") == "1",
                     "Texterkennung dauert ~20 s; mit GRAUZONE_OCR_TEST=1 einschalten")
class Scan(unittest.TestCase):
    def test_scanseite_per_texterkennung_geschwaerzt(self):
        import easyocr
        reader = easyocr.Reader(["de", "en"], gpu=False, verbose=False)
        doc = pymupdf.open()
        bild_seite(doc, ["Sehr geehrte Frau Erika Mustermann,", "Telefon 0221 1234567"])
        daten = als_bytes(doc)
        seiten = scanne(daten, ocr_reader=reader)
        self.assertEqual("Texterkennung", seiten[0][3])
        self.assertTrue(any("Mustermann" in f.text for f in seiten[0][2]))
        ergebnis, anzahl = exportiere(daten, seiten)
        self.assertGreater(anzahl, 0)
        # Nach dem Schwärzen darf die Texterkennung den Namen nicht mehr lesen
        neu = pymupdf.open(stream=ergebnis, filetype="pdf")
        zeilen = E.woerter_aus_ocr(reader, neu[0])
        gelesen = " ".join(w.text for z in zeilen for w in z)
        self.assertNotIn("Mustermann", gelesen)
        self.assertIn("geehrte", gelesen)


class Sensibel(unittest.TestCase):
    """Kennnummer, Geburtsdatum und Gesundheitsangabe werden physisch entfernt,
    Feldbezeichnungen und andere Daten bleiben lesbar (erfundene Angaben)."""
    def test_export(self):
        doc = pymupdf.open()
        text_seite(doc, ["Steuer-ID: 86095742719", "geboren am 03.04.1985",
                         "Diagnose: Asthma bronchiale", "Termin am 01.02.2026", "Aktenzeichen: 32-1234/25"])
        daten = als_bytes(doc)
        # Nur die neuen Arten schwärzen: Das kleine Sprachmodell meldet hier zusätzlich
        # „Steuer-ID“ oder das Termin-Datum als Organisation/Ort (unter „zu prüfen“)
        ergebnis, _ = exportiere(daten, scanne(daten), lambda p, f: f.art in {"KENN", "GEB", "GES"})
        text = pymupdf.open(stream=ergebnis, filetype="pdf")[0].get_text()
        for weg in ("86095742719", "03.04.1985", "Asthma"):
            self.assertNotIn(weg, text)
        for bleibt in ("Steuer-ID:", "geboren am", "Diagnose:", "01.02.2026", "32-1234/25"):
            self.assertIn(bleibt, text)


if __name__ == "__main__":
    unittest.main()
