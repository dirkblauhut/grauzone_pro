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


class EinzelneSeiten(unittest.TestCase):
    def test_seitenauswahl(self):
        self.assertEqual([0, 1, 2, 4], E.seitenauswahl("1-3, 5", 5))
        self.assertEqual([0, 1, 2], E.seitenauswahl("  ", 3))
        self.assertEqual([1, 2], E.seitenauswahl("3-2", 3))
        for falsch in ("0", "4", "a", "1-x", ","):
            with self.assertRaises(ValueError, msg=falsch):
                E.seitenauswahl(falsch, 3)

    def test_nur_gewaehlte_seiten_im_export(self):
        doc = pymupdf.open()
        for nr in range(3):
            seite = doc.new_page()
            seite.insert_text((72, 72), f"Blatt {nr + 1}: Erika Mustermann", fontsize=11)
        daten = doc.tobytes()
        rect = (72 + 0, 60, 300, 76)
        balken = {p: [rect] for p in range(3)}
        export, anzahl = E.schwaerze(daten, balken, [0, 2])
        neu = pymupdf.open(stream=export, filetype="pdf")
        self.assertEqual(2, len(neu))
        self.assertEqual(2, anzahl, "nur Balken der exportierten Seiten")
        self.assertNotIn("Mustermann", "".join(p.get_text() for p in neu))
        # Prüfung mit Seitenzahlen des Originals
        self.assertEqual([], E.pruefe_export(export, {0: [rect], 1: [rect]}, nummern=[0, 2]))
        ohne, _ = E.schwaerze(daten, {}, [0, 2])
        meldung = E.pruefe_export(ohne, {0: [rect], 1: [rect]}, nummern=[0, 2])
        self.assertTrue(any(m.startswith("Seite 3:") for m in meldung), meldung)


def roh_enthaelt(daten: bytes, wort: str) -> bool:
    """Sucht ein Wort in allen Objekten und entpackten Datenströmen des PDFs (auch hex/UTF-16)."""
    doc = pymupdf.open(stream=daten, filetype="pdf")
    muster = [wort.encode(), wort.encode().hex().encode(), wort.encode("utf-16-be").hex().encode()]
    for x in range(1, doc.xref_length()):
        teile = [doc.xref_object(x, compressed=True).encode("latin1", "ignore")]
        try:
            if doc.xref_is_stream(x):
                teile.append(doc.xref_stream(x) or b"")
        except Exception:
            pass
        blob = b" ".join(teile)
        if any(m in blob or m in blob.lower() for m in muster):
            return True
    return False


class VerborgeneInhalte(unittest.TestCase):
    """Behoben (0.8.0, Projektprüfung 2026-11-13): Diese Inhalte überlebten den Export, und
    die Exportprüfung meldete „bestanden“. Erfundene Daten."""

    @staticmethod
    def seite():
        from hilfen import text_seite
        doc = pymupdf.open()
        return doc, text_seite(doc, ["Sehr geehrte Frau Erika Mustermann,", "Telefon 0221 1234567"])

    def exportiert(self, doc, *geheim):
        from hilfen import scanne, exportiere
        daten = doc.tobytes()
        meldungen_vorher = E.verborgene_reste(pymupdf.open(stream=daten, filetype="pdf"))
        seiten = scanne(daten)
        ergebnis, _ = exportiere(daten, seiten)
        rechtecke = {p: [E.wort_rechteck(s[1][i], f) for f in s[2] for i in f.woerter]
                     for p, s in enumerate(seiten)}
        self.assertEqual([], E.pruefe_export(ergebnis, rechtecke))
        for wort in geheim:
            self.assertFalse(roh_enthaelt(ergebnis, wort), f"„{wort}“ steht noch in der Datei")
        return meldungen_vorher

    def test_text_ausserhalb_des_seitenausschnitts(self):
        doc, seite = self.seite()
        seite.insert_text((72, 760), "Vermerk: Frau Berta Musterfrau", fontsize=11)
        seite.set_cropbox(pymupdf.Rect(0, 0, 595, 600))
        vorher = self.exportiert(doc, "Musterfrau", "Mustermann")
        self.assertTrue(any("Seitenausschnitt" in m for m in vorher), "Prüfung erkennt den Beschnitt")

    def test_verschobener_ursprung_ist_kein_beschnitt(self):
        doc, seite = self.seite()
        seite.set_mediabox(pymupdf.Rect(-20, -30, 575, 812))
        self.assertEqual([], E.verborgene_reste(pymupdf.open(stream=doc.tobytes(), filetype="pdf")))
        seite = E.oeffne_pdf(doc.tobytes())[0]
        self.assertEqual((595, 842), (round(seite.rect.width), round(seite.rect.height)))

    def test_ausgeblendete_ebene(self):
        doc, seite = self.seite()
        seite.insert_text((72, 200), "Frau Berta Musterfrau", fontsize=11, oc=doc.add_ocg("Verborgen", on=False))
        vorher = self.exportiert(doc, "Musterfrau")
        self.assertIn("Ausgeblendete Ebenen vorhanden.", vorher)

    def test_verknuepfung_mit_mail_adresse(self):
        doc, seite = self.seite()
        seite.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(72, 300, 300, 320),
                           "uri": "mailto:berta.musterfrau@example.org"})
        vorher = self.exportiert(doc, "musterfrau@")
        self.assertTrue(any("Verknüpfung" in m for m in vorher))

    def test_interne_verknuepfung_bleibt(self):
        doc, _ = self.seite()
        doc.new_page()
        doc[0].insert_link({"kind": pymupdf.LINK_GOTO, "from": pymupdf.Rect(72, 300, 300, 320), "page": 1})
        ergebnis, _ = E.schwaerze(doc.tobytes(), {0: []})
        self.assertEqual(1, len(pymupdf.open(stream=ergebnis, filetype="pdf")[0].get_links()))

    def test_seitenbezeichnung(self):
        doc, _ = self.seite()
        doc.set_page_labels([{"startpage": 0, "prefix": "Musterfrau-", "style": "D", "firstpagenum": 1}])
        self.assertIn("Seitenbezeichnungen vorhanden.", self.exportiert(doc, "Musterfrau"))

    def test_javascript_beim_oeffnen(self):
        doc, _ = self.seite()
        doc.xref_set_key(doc.pdf_catalog(), "OpenAction", "<</S/JavaScript/JS(app.alert\\('Akte Musterfrau'\\))>>")
        self.assertIn("JavaScript oder automatische Aktionen vorhanden.", self.exportiert(doc, "Musterfrau"))

    def test_strukturbaum_und_vorschaubild(self):
        doc, seite = self.seite()
        alt = doc.get_new_xref()
        doc.update_object(alt, "<</Type/StructElem/S/Figure/Alt(Foto von Berta Musterfrau)>>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"<</Type/StructTreeRoot/K {alt} 0 R>>")
        bild = doc.get_new_xref()
        doc.update_object(bild, "<<>>")
        doc.update_stream(bild, b"Vorschau Musterfrau")
        doc.xref_set_key(seite.xref, "Thumb", f"{bild} 0 R")
        vorher = self.exportiert(doc, "Musterfrau")
        self.assertIn("Strukturbaum (z. B. Alternativtexte) vorhanden.", vorher)
        self.assertIn("Vorschaubilder der Seiten vorhanden.", vorher)


if __name__ == "__main__":
    unittest.main()
