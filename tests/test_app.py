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


def haken(at):
    """Nur die Haken der Fundstellen (nicht z. B. „Auch in künftigen Dokumenten …“)."""
    return [c for c in at.checkbox if (c.key or "").startswith("cb_")]


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
        self.assertTrue(haken(at), "Fundstellen auf Seite 1 als Haken")

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
        erster = haken(at)[0]
        erster.uncheck().run()
        legende = next(m.value for m in at.markdown if "class='gz-legende'" in m.value)
        self.assertIn("1 freigegeben", legende)
        self.assertIsNone(at.session_state.export, "alter Export passt nicht mehr zur Auswahl")

    def test_sammelaktion_gilt_fuer_alle_seiten_und_lernt_nicht(self):
        at = self.at
        knopf(at, "Alle freigeben").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertEqual([], at.session_state.kb["whitelist"], "Sammelaktion darf nichts lernen")
        self.assertTrue(at.session_state.auswahl)
        self.assertFalse(any(at.session_state.auswahl.values()), "alle Seiten freigegeben")
        self.assertFalse(any(c.value for c in haken(at)))
        knopf(at, "Alle schwärzen").click().run()
        self.assertTrue(all(at.session_state.auswahl.values()))
        self.assertTrue(all(c.value for c in haken(at)))

    def test_haken_von_hand_lernt(self):
        at = self.at
        name = haken(at)[0].label.strip("*")
        haken(at)[0].uncheck().run()
        self.assertIn(name, at.session_state.kb["whitelist"])

    def test_suche_filtert_fundstellen(self):
        at = self.at
        at.text_input(key="suche").input("0221").run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertEqual(["**0221 1234567**"], [c.label for c in haken(at)])
        self.assertIn("Alle freigeben (1)", knopf(at, "Alle freigeben").label)

    def test_ansicht_ergebnis_zeigt_geschwaerztes_pdf(self):
        at = self.at
        for ansicht in ("Ergebnis", "Beide"):
            at.session_state.ansicht = ansicht
            at.run()
            self.assertEqual([], [str(e.value) for e in at.exception])
        _, erg = at.session_state.ergebnis
        text = "".join(p.get_text() for p in erg)
        self.assertNotIn("Mustermann", text)
        self.assertIn("Sehr geehrte Frau", text)

    def test_gleiche_angabe_auf_allen_seiten(self):
        at = self.at
        name = haken(at)[0].label.strip("*")
        self.assertEqual("Erika Mustermann", name)
        haken(at)[0].uncheck().run()
        self.assertFalse(at.session_state.auswahl[(2, "erika mustermann")], "auch Seite 3")

    def test_gleiche_angabe_nur_diese_seite_wenn_aus(self):
        at = self.at
        at.toggle(key="gemeinsam").set_value(False).run()
        haken(at)[0].uncheck().run()
        self.assertNotEqual(False, at.session_state.auswahl.get((2, "erika mustermann")))

    def test_rueckgaengig_und_wiederholen(self):
        at = self.at
        name = haken(at)[0].label.strip("*")
        haken(at)[0].uncheck().run()
        self.assertIn(name, at.session_state.kb["whitelist"])
        knopf(at, "↶").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertTrue(haken(at)[0].value)
        self.assertNotIn(name, at.session_state.kb["whitelist"], "Lernen wird mit zurückgenommen")
        knopf(at, "↷").click().run()
        self.assertFalse(haken(at)[0].value)
        self.assertIn(name, at.session_state.kb["whitelist"])
        knopf(at, "Alle freigeben").click().run()
        knopf(at, "↶").click().run()
        self.assertFalse(haken(at)[0].value, "Sammelaktion zurückgenommen, Haken von Hand bleibt")

    def test_export_einzelner_seiten(self):
        at = self.at
        at.text_input(key="export_seiten").input("9").run()
        self.assertTrue(at.error, "ungültige Seite wird gemeldet")
        self.assertTrue(knopf(at, "Schwärzen & exportieren").disabled)
        at.text_input(key="export_seiten").input("3").run()
        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        pdf, md, _, _, meldungen, protokoll, _ = at.session_state.export
        doc = pymupdf.open(stream=pdf, filetype="pdf")
        self.assertEqual(1, len(doc))
        self.assertIn("Absender", doc[0].get_text())
        self.assertNotIn("Mustermann", doc[0].get_text())
        self.assertEqual([], meldungen)
        self.assertIn("Exportiert wurden nur die Seiten 3 (1 von 3)", protokoll)
        self.assertIn("## Seite 3", md)
        self.assertNotIn("## Seite 1", md)

    def begriff(self, text, merken=False):
        at = self.at
        next(t for t in at.text_input if t.label == "Begriff schwärzen").input(text)
        if merken:
            at.checkbox(key="begriff_merken").check()
        knopf(at, "Schwärzen").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        return at

    def test_begriff_nur_dieses_dokument_mit_trefferzahl(self):
        at = self.begriff("Gruessen")
        self.assertEqual([], at.session_state.kb["blacklist"], "ohne Haken nicht gelernt")
        self.assertEqual(["Gruessen"], at.session_state.begriffe)
        self.assertTrue(any("1 Treffer, Seite 1 (1)" in m.value for m in at.success))
        self.assertIn("**Gruessen**", [c.label for c in haken(at)])

    def test_begriff_dauerhaft(self):
        at = self.begriff("Gruessen", merken=True)
        self.assertEqual(["Gruessen"], at.session_state.kb["blacklist"])
        self.assertEqual([], at.session_state.begriffe)

    def test_begriff_ohne_treffer_verweist_auf_markieren(self):
        at = self.begriff("Unbekanntwort")
        self.assertTrue(any("steht nicht im erkannten Text" in m.value for m in at.warning))

    def test_bereich_von_hand_wird_geschwaerzt(self):
        at = self.at
        # Bereich über der Zeile „Mit freundlichen Gruessen“ (Seite 1, dritte Zeile ab y=72+36)
        at.session_state.hand = [{"id": 1, "p": 0, "art": "BEREICH", "rect": (60, 95, 400, 112),
                                  "wort": None, "text": "Bereich", "an": True}]
        at.session_state.hand_nr = 1
        at.run()
        self.assertIn("**Bereich**", [c.label for c in at.checkbox])
        knopf(at, "Schwärzen & exportieren").click().run()
        self.assertEqual([], [str(e.value) for e in at.exception])
        pdf, md, _, _, meldungen, protokoll, _ = at.session_state.export
        text = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
        self.assertNotIn("Gruessen", text)
        self.assertEqual([], meldungen)
        self.assertIn("von Hand markiert (Wörter und Bereiche): 1", protokoll)
        self.assertNotIn("Gruessen", md, "Markdown ersetzt die Wörter im Bereich")
        knopf(at, "🗑").click().run()
        self.assertEqual([], at.session_state.hand)
        knopf(at, "↶").click().run()
        self.assertEqual(1, len(at.session_state.hand), "Löschen lässt sich zurücknehmen")


if __name__ == "__main__":
    unittest.main()
