"""Erkennung ohne PDF: Muster, Grenzen von Fundstellen, Rechtecke, Markdown.
Behobene Fehler aus PROJEKTSTAND.md Abschnitt 3 sind hier festgehalten."""
import unittest

from hilfen import E, nlp


def zeilen_aus(text):
    """Baut Wörter mit erfundenen Positionen (je Zeichen 6 pt, je Zeile 14 pt)."""
    zeilen = []
    for nr, zeile in enumerate(text.split("\n")):
        woerter, x = [], 72.0
        for wort in zeile.split():
            woerter.append(E.Wort(wort, (x, 72 + nr * 14, x + 6 * len(wort), 82 + nr * 14)))
            x += 6 * (len(wort) + 1)
        if woerter:
            zeilen.append(woerter)
    return zeilen


def funde(text, mit_nlp=False, vornamen=(), gelernt=()):
    t, woerter = E.seitentext(zeilen_aus(text))
    return E.finde(t, woerter, nlp() if mit_nlp else None, set(vornamen), list(gelernt))


def arten(fs):
    return {(f.text, f.art) for f in fs}


class Muster(unittest.TestCase):
    def test_telefon_wird_erkannt(self):
        self.assertIn(("0221 1234567", "TEL"), arten(funde("Telefon: 0221 1234567")))

    def test_datum_ist_keine_telefonnummer(self):
        # Behoben: Datum wurde als Telefonnummer erkannt
        self.assertEqual([], [f for f in funde("Musterstadt, den 01.02.2026") if f.art == "TEL"])

    def test_kurze_zahl_ist_keine_telefonnummer(self):
        self.assertEqual([], [f for f in funde("Aktenzeichen 0815") if f.art == "TEL"])

    def test_mail_iban_plz(self):
        a = arten(funde("erika.mustermann@example.org\nDE02 1203 0000 0000 2020 51\n12345 Musterstadt"))
        self.assertIn(("erika.mustermann@example.org", "MAIL"), a)
        self.assertIn(("DE02 1203 0000 0000 2020 51", "IBAN"), a)
        self.assertIn(("12345 Musterstadt", "ADR"), a)

    def test_strasse_mit_hausnummer(self):
        self.assertIn(("Musterweg 12a", "ADR"), arten(funde("wohnhaft Musterweg 12a")))

    def test_anrede_bleibt_lesbar(self):
        fs = funde("Sehr geehrte Frau Dr. Erika Mustermann,")
        self.assertIn(("Erika Mustermann", "PER"), arten(fs))
        self.assertFalse(any("Frau" in f.text or "Dr." in f.text for f in fs))

    def test_vornamenliste_nimmt_nachnamen_mit(self):
        self.assertIn(("Erika Mustermann", "PER"), arten(funde("Gez. Erika Mustermann", vornamen={"erika"})))

    def test_gelernter_begriff_unabhaengig_von_gross_klein(self):
        self.assertIn(("MUSTERHOF", "LISTE"), arten(funde("Gut MUSTERHOF liegt am See", gelernt=["Musterhof"])))

    def test_gelernter_begriff_nicht_in_anderem_wort(self):
        self.assertEqual([], funde("Musterhofweg", gelernt=["Musterhof"]))


class Grenzen(unittest.TestCase):
    def test_keine_fundstelle_ueber_zeilenumbruch(self):
        # Behoben: Absender und Anschrift wurden eine Fundstelle
        for f in funde("Erika Mustermann\nMusterweg 12\n12345 Musterstadt", mit_nlp=nlp() is not None):
            self.assertNotIn("\n", f.text)
            self.assertNotIn("Mustermann Musterweg", f.text)

    def test_spacy_findet_person(self):
        if nlp() is None:
            self.skipTest("kein spaCy-Modell installiert")
        fs = funde("Gestern traf Erika Mustermann in Musterstadt ein.", mit_nlp=True)
        self.assertTrue(any("Mustermann" in f.text for f in fs))

    def test_fund_kennt_seine_woerter(self):
        t, woerter = E.seitentext(zeilen_aus("Frau Erika Mustermann wohnt hier"))
        f = next(f for f in E.finde(t, woerter, None, set(), []) if f.art == "PER")
        self.assertEqual(["Erika", "Mustermann"], [woerter[i].text for i in f.woerter])


class Rechtecke(unittest.TestCase):
    def test_satzzeichen_bleibt_frei(self):
        # Schwärzung auf Wortebene: "Mustermann," ohne Komma
        t, woerter = E.seitentext(zeilen_aus("Frau Erika Mustermann, bitte"))
        f = next(f for f in E.finde(t, woerter, None, set(), []) if f.art == "PER")
        wort = woerter[f.woerter[-1]]
        r = E.wort_rechteck(wort, f)
        self.assertLess(r[2], wort.rect[2])          # endet vor dem Komma
        self.assertLessEqual(r[0], wort.rect[0])     # beginnt am Wortanfang

    def test_ganzes_wort_mit_kleinem_rand(self):
        w = E.Wort("Mustermann", (100, 100, 160, 110), start=0, ende=10)
        r = E.wort_rechteck(w, E.Fund("Mustermann", "PER", [0], 0, 10))
        self.assertEqual((99, 99, 161, 111), r)

    def test_ocr_wort_mit_mehr_rand(self):
        # Behoben: Buchstabenreste neben Balken bei Scans
        w = E.Wort("Mustermann", (100, 100, 160, 110), start=0, ende=10, ocr=True)
        r = E.wort_rechteck(w, E.Fund("Mustermann", "PER", [0], 0, 10))
        self.assertEqual((98, 98, 162, 112), r)


class Markdown(unittest.TestCase):
    def test_platzhalter_nummeriert_und_wiederverwendet(self):
        text = "Frau Erika Mustermann schreibt.\nFrau Erika Mustermann und Herr Max Muster.\n"
        t, woerter = E.seitentext(zeilen_aus(text))
        fs = E.finde(t, woerter, None, set(), [])
        md, anzahl = E.markdown([(0, t, fs)], lambda p, f: True)
        self.assertEqual(3, anzahl)
        self.assertEqual(2, md.count("[Person 1]"))
        self.assertIn("[Person 2]", md)
        self.assertNotIn("Mustermann", md)

    def test_abgewaehlt_bleibt_stehen(self):
        t, woerter = E.seitentext(zeilen_aus("Frau Erika Mustermann"))
        fs = E.finde(t, woerter, None, set(), [])
        md, anzahl = E.markdown([(0, t, fs)], lambda p, f: False)
        self.assertEqual(0, anzahl)
        self.assertIn("Erika Mustermann", md)

    def test_markdown_zeichen_maskiert(self):
        t, woerter = E.seitentext(zeilen_aus("1. Punkt\n# kein Titel\nText_mit*Stern"))
        md, _ = E.markdown([(0, t, [])], lambda p, f: True)
        self.assertIn("1\\. Punkt", md)
        self.assertIn("\\# kein Titel", md)
        self.assertIn("Text\\_mit\\*Stern", md)

    def test_nicht_gescannte_seiten_genannt(self):
        md, _ = E.markdown([], lambda p, f: True, nicht_gescannt=[1, 2])
        self.assertIn("Seite 2, 3", md)


class _Ent:
    def __init__(self, label, start, ende):
        self.label_, self.start_char, self.end_char = label, start, ende


class _Modell:
    """Ersatz für spaCy: meldet vorgegebene Wörter als Entität (unabhängig vom Modell)."""
    def __init__(self, **eintraege):
        self.eintraege = eintraege

    def __call__(self, text):
        class Doc:
            pass
        d = Doc()
        d.ents = [_Ent(label, text.index(wort), text.index(wort) + len(wort))
                  for wort, label in self.eintraege.items() if wort in text]
        return d


def funde_mit(text, modell, vornamen=()):
    t, woerter = E.seitentext(zeilen_aus(text))
    return E.finde(t, woerter, modell, set(vornamen), [])


def fund(fs, text):
    return next(f for f in fs if f.text == text)


class Begruendung(unittest.TestCase):
    def test_anrede_ist_eindeutig_mit_grund(self):
        f = fund(funde("Sehr geehrte Frau Erika Mustermann,"), "Erika Mustermann")
        self.assertIn("ANREDE", f.quellen)
        self.assertTrue(E.ist_eindeutig(f))
        self.assertIn("Name nach Anrede (Frau, Herr)", E.begruendung(f))

    def test_nur_sprachmodell_ist_zu_pruefen(self):
        f = fund(funde_mit("Das Gutachten stammt von Musterfrau.", _Modell(Musterfrau="PER")), "Musterfrau")
        self.assertEqual(("MODELL_PER",), f.quellen)
        self.assertFalse(E.ist_eindeutig(f))

    def test_zwei_quellen_sind_eindeutig(self):
        f = fund(funde_mit("Gez. Erika Mustermann", _Modell(**{"Erika Mustermann": "PER"}), vornamen={"erika"}),
                 "Erika Mustermann")
        self.assertEqual({"MODELL_PER", "VORNAME"}, set(f.quellen))
        self.assertTrue(E.ist_eindeutig(f))

    def test_iban_pruefziffer(self):
        gueltig = fund(funde("DE02 1203 0000 0000 2020 51"), "DE02 1203 0000 0000 2020 51")
        falsch = fund(funde("DE03 1203 0000 0000 2020 51"), "DE03 1203 0000 0000 2020 51")
        ocr = fund(funde("DEO2 1203 000o 000o 2020 51"), "DEO2 1203 000o 000o 2020 51")
        self.assertEqual(("IBAN",), gueltig.quellen)
        self.assertTrue(E.ist_eindeutig(gueltig))
        self.assertTrue(E.ist_eindeutig(ocr), "OCR-Verwechslungen vor der Prüfziffer ersetzen")
        # Die Teilfolge, die wie eine Telefonnummer aussieht, begründet die IBAN nicht
        self.assertEqual(("IBAN_UNSICHER",), falsch.quellen)
        self.assertFalse(E.ist_eindeutig(falsch))
        self.assertEqual("IBAN", falsch.art, "auch ohne gültige Prüfziffer gefunden und geschwärzt")


if __name__ == "__main__":
    unittest.main()
