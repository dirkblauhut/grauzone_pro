"""Die Streamlit-Oberfläche headless über AppTest: Start, Scannen, Export."""
import os
import shutil
import tempfile
import unittest

import pymupdf
import streamlit as st

from hilfen import PROJEKT
from test_schwaerzung import mehrseitig


def starte(datei=None):
    """Startet app.py in einem leeren Arbeitsordner, damit Wissensbasis und
    Vornamenliste des Nutzers unberührt bleiben; mit datei statt des Hochladens
    (AppTest kann keine Datei hochladen). Liefert (AppTest, Aufräumfunktion)."""
    from streamlit.testing.v1 import AppTest
    original = st.file_uploader
    if datei is not None:
        class Hochgeladen:
            name = "probe.pdf"

            def getvalue(self):
                return datei
        st.file_uploader = lambda *a, **k: Hochgeladen()
    alt, ordner = os.getcwd(), tempfile.mkdtemp(prefix="grauzone-test-")
    os.chdir(ordner)   # app.py liest knowledge_base.json und vornamen.txt relativ

    def aufraeumen():
        st.file_uploader = original
        os.chdir(alt)
        shutil.rmtree(ordner, ignore_errors=True)
    try:
        at = AppTest.from_file(os.path.join(PROJEKT, "app.py"), default_timeout=120).run()
    except Exception:
        aufraeumen()
        raise
    return at, aufraeumen


def knopf(at, text):
    return next(b for b in at.button if text in b.label)


class AppStart(unittest.TestCase):
    def test_app_startet_ohne_dokument(self):
        at, zurueck = starte()
        zurueck()
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertTrue(any("Grauzone <b>PRO</b>" in m.value for m in at.markdown))


class AppDurchlauf(unittest.TestCase):
    def setUp(self):
        self.at, self.zurueck = starte(mehrseitig())
        knopf(self.at, "Alle Seiten scannen").click().run()

    def tearDown(self):
        self.zurueck()

    def test_scannen_blaettern_exportieren(self):
        at = self.at
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertEqual(3, len(at.session_state.woerter))
        self.assertTrue(at.checkbox, "Fundstellen auf Seite 1 als Haken")

        knopf(at, "▶").click().run()
        self.assertEqual(2, at.session_state.seite)
        knopf(at, "◀").click().run()
        self.assertEqual(1, at.session_state.seite)

        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        pdf = at.session_state.export[0]
        text = "".join(p.get_text() for p in pymupdf.open(stream=pdf, filetype="pdf"))
        self.assertNotIn("Mustermann", text)
        self.assertIn("Sehr geehrte Frau", text)

    def test_protokoll_ohne_originaldaten(self):
        at = self.at
        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        protokoll = at.session_state.export[5]
        self.assertIn("Ergebnis: **bestanden**", protokoll)
        self.assertIn("SHA-256", protokoll)
        for verboten in ("Mustermann", "probe", "Musterstadt", "0221"):
            self.assertNotIn(verboten, protokoll)

    def test_dateinamen_ohne_originalnamen(self):
        # Der Originalname (hier „probe.pdf“) kann Personennamen enthalten
        at = self.at
        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        pdf, md, protokoll = at.session_state.export[6]
        stempel = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}"
        self.assertRegex(pdf, rf"^{stempel}_Anonymisiert\.pdf$")
        self.assertRegex(md, rf"^{stempel}_Anonymisiert\.md$")
        self.assertRegex(protokoll, rf"^{stempel}_Pruefprotokoll\.md$")
        self.assertEqual(pdf[:16], md[:16], "PDF und Markdown mit demselben Zeitstempel")
        self.assertEqual(pdf[:16], protokoll[:16], "Protokoll mit demselben Zeitstempel")

    def test_haken_entfernen_wirkt_sofort(self):
        # Behoben (Testversion): Vorschau und Zähler wurden vor der Liste gezeichnet
        # und zeigten die alte Auswahl
        at = self.at
        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertIsNotNone(at.session_state.export)
        haken = at.checkbox[0]
        haken.uncheck().run()
        legende = next(m.value for m in at.markdown if "class='gz-legende'" in m.value)
        self.assertIn("1 freigegeben", legende)
        self.assertIsNone(at.session_state.export, "alter Export passt nicht mehr zur Auswahl")


if __name__ == "__main__":
    unittest.main()
