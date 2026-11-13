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


def ein(text, **kw):
    """(Text, Art, eindeutig) aller Fundstellen."""
    return {(f.text, f.art, E.ist_eindeutig(f)) for f in funde(text, **kw)}


class Kennnummern(unittest.TestCase):
    # Beispielnummern aus öffentlichen Musterangaben (erfundene Personen)
    def test_steuer_id_mit_pruefziffer(self):
        self.assertIn(("86095742719", "KENN", True), ein("Steuer-ID: 86095742719"))
        self.assertIn(("86 095 742 719", "KENN", True), ein("Identifikationsnummer 86 095 742 719"))
        # Prüfziffer falsch: trotzdem schwärzen, aber prüfen
        self.assertIn(("12345678901", "KENN", False), ein("Steuer-ID: 12345678901"))

    def test_steuer_id_ohne_feld_nur_zu_pruefen(self):
        self.assertIn(("86095742719", "KENN", False), ein("Die Nummer 86095742719 steht unten."))
        self.assertEqual(set(), ein("Die Nummer 12345678901 steht unten."), "ohne Feld nur mit gültiger Prüfziffer")

    def test_versicherungsnummern(self):
        self.assertIn(("15 070649 C 103", "KENN", True), ein("Rentenversicherungsnummer: 15 070649 C 103"))
        self.assertIn(("A123456780", "KENN", True), ein("KV-Nummer: A123456780"))
        self.assertIn(("123456789A123", "KENN", True), ein("Versicherungsnummer: 123456789A123"))

    def test_ausweis_karte_ip(self):
        self.assertIn(("T220001293", "KENN", True), ein("Ausweisnummer: T220001293"))
        self.assertIn(("4111 1111 1111 1111", "KENN", False), ein("Karte 4111 1111 1111 1111"))
        self.assertEqual(set(), ein("Karte 4111 1111 1111 1112"), "Luhn-Prüfung")
        self.assertIn(("192.168.10.24", "KENN", False), ein("Zugriff von 192.168.10.24 protokolliert"))

    def test_feld_mit_wert(self):
        self.assertIn(("K-4711-0815", "KENN", True), ein("Kundennummer: K-4711-0815"))
        self.assertIn(("V-2024/0815", "KENN", True), ein("Vertragsnummer V-2024/0815 vom 1. Mai"))
        self.assertIn(("K-AB 1234", "KENN", True), ein("Kennzeichen: K-AB 1234"))
        self.assertIn(("COBADEFFXXX", "KENN", True), ein("BIC: COBADEFFXXX"))
        # Der Wert endet vor dem nächsten Wort
        self.assertIn(("4711", "KENN", True), ein("Kundennummer 4711 Sehr geehrte Frau"))

    def test_aktenzeichen_bleibt_lesbar(self):
        # Vom Nutzer festgelegt: Aktenzeichen und Vorgangsnummern nicht schwärzen
        self.assertEqual(set(), ein("Aktenzeichen: 32-1234/25"))
        self.assertEqual(set(), ein("Az.: 32-1234/25"))


class Geburtsdatum(unittest.TestCase):
    def test_nur_mit_kontext(self):
        self.assertIn(("03.04.1985", "GEB", True), ein("geboren am 03.04.1985"))
        self.assertIn(("3. April 1985", "GEB", True), ein("geb. 3. April 1985 in Musterstadt"))
        self.assertIn(("03.04.85", "GEB", True), ein("Geburtsdatum: 03.04.85"))
        self.assertIn(("Musterstadt", "ORT", True), ein("Geburtsort: Musterstadt"))

    def test_andere_daten_und_geburtsname_bleiben(self):
        # Vom Nutzer festgelegt: andere Daten und Alter nicht schwärzen
        self.assertEqual(set(), ein("Termin am 03.04.2025, Frist 30 Tage"))
        self.assertEqual(set(), ein("Die Antragstellerin ist 47 Jahre alt."))
        self.assertFalse(any(a == "GEB" for _, a, _ in ein("Erika Mustermann, geb. Schmidt")))


class Gesundheit(unittest.TestCase):
    def test_feld_und_wortliste(self):
        self.assertIn(("F32.1 mittelgradige depressive Episode", "GES", True),
                      ein("Diagnose: F32.1 mittelgradige depressive Episode. Weiter im Text."))
        self.assertIn(("30 mg Ramipril", "GES", True), ein("Medikation: 30 mg Ramipril"))
        self.assertIn(("E11.9", "GES", True), ein("ICD-10: E11.9"))

    def test_kontext(self):
        self.assertIn(("Diabetes mellitus Typ 2", "GES", True), ein("Patient leidet an Diabetes mellitus Typ 2"))
        self.assertIn(("Angststörung", "GES", True), ein("wegen einer Angststörung in ärztlicher Behandlung"))
        # Wendung ohne bekannte Krankheit: gefunden, aber zu prüfen
        self.assertIn(("Zeitdruck", "GES", False), ein("Er leidet unter Zeitdruck"))

    def test_behinderung(self):
        self.assertIn(("Grad der Behinderung von 50", "GES", False), ein("Grad der Behinderung von 50"))
        self.assertIn(("schwerbehindert", "GES", False), ein("Sie ist schwerbehindert."))

    def test_platzhalter_im_markdown(self):
        t, woerter = E.seitentext(zeilen_aus("Diagnose: Asthma\nKundennummer: 4711"))
        fs = E.finde(t, woerter, None, set(), [])
        md, _ = E.markdown([(0, t, fs)], lambda p, f: True)
        self.assertIn("[Gesundheitsangabe 1]", md)
        self.assertIn("[Kennnummer 1]", md)


def ocr_zeile(*teile, y=100.0, h=10.0):
    """Wörter aus der Texterkennung: (Text, x0, x1[, y0, y1]) -> eine Zeile."""
    woerter = []
    for t in teile:
        text, x0, x1 = t[:3]
        y0, y1 = (t[3], t[4]) if len(t) > 3 else (y, y + h)
        woerter.append(E.Wort(text, (x0, y0, x1, y1), ocr=True))
    return woerter


class BegriffTolerant(unittest.TestCase):
    def test_verwechslungen_nur_bei_texterkennung(self):
        t, w = E.seitentext([ocr_zeile(("Herr", 0, 30), ("FEL1X", 40, 80), ("Beispiel", 90, 150))])
        genau, nah = E.begriff_treffer(t, w, "Felix")
        self.assertEqual([], genau)
        self.assertEqual(["FEL1X"], [t[s_:e_] for s_, e_ in nah])
        # Gleicher Text aus der Textebene: nur genaue Treffer
        t2, w2 = E.seitentext(zeilen_aus("Herr FEL1X Beispiel"))
        self.assertEqual(([], []), E.begriff_treffer(t2, w2, "Felix"))

    def test_ein_zeichen_abweichung_ab_fuenf_buchstaben(self):
        t, w = E.seitentext([ocr_zeile(("Musterrnann", 0, 80), ("Muster", 90, 130))])
        self.assertEqual(["Musterrnann"], [t[s_:e_] for s_, e_ in E.begriff_treffer(t, w, "Mustermann")[1]])
        t, w = E.seitentext([ocr_zeile(("Mayr", 0, 30))])
        self.assertEqual([], E.begriff_treffer(t, w, "Maier")[1], "kurze Wörter nur bei gleicher Form")

    def test_mehrteiliger_begriff_als_ein_wort(self):
        t, w = E.seitentext([ocr_zeile(("ERIKAMUSTERMANN", 0, 120))])
        self.assertEqual(1, len(E.begriff_treffer(t, w, "Erika Mustermann")[1]))

    def test_begriff_nur_fuer_dieses_dokument(self):
        t, w = E.seitentext(zeilen_aus("Gut Musterhof liegt am See"))
        f = fund(E.finde(t, w, None, set(), [], ["Musterhof"]), "Musterhof")
        self.assertEqual(("HAND", ("BEGRIFF",)), (f.art, f.quellen))
        self.assertTrue(E.ist_eindeutig(f))


class Formularzeilen(unittest.TestCase):
    def test_handschrift_rechts_neben_feldbezeichnung(self):
        # Handschrift größer und etwas höher als die gedruckte Bezeichnung, Text falsch gelesen
        zeile1 = ocr_zeile(("Herr/Frau", 0, 50), ("8LAVHVT", 80, 160, 94, 116), ("FEL1X", 180, 230, 95, 115))
        zeile2 = ocr_zeile(("geboren", 0, 40, 130, 140), ("am", 44, 56, 130, 140), ("2S.O9.2OO8", 90, 170, 125, 145))
        zeile3 = ocr_zeile(("hat", 0, 15, 160, 170), ("bestanden", 300, 350, 160, 170))
        t, w = E.seitentext([zeile1, zeile2, zeile3])
        fs = E.finde(t, w, None, set(), [])
        self.assertIn(("8LAVHVT FEL1X", "PER", False), {(f.text, f.art, E.ist_eindeutig(f)) for f in fs})
        self.assertIn(("2S.O9.2OO8", "GEB", False), {(f.text, f.art, E.ist_eindeutig(f)) for f in fs})
        self.assertFalse(any("bestanden" in f.text for f in fs))

    def test_nur_am_zeilenanfang_und_nur_bei_scans(self):
        t, w = E.seitentext([ocr_zeile(("Danke", 0, 30), ("Frau", 40, 60), ("XYZ", 70, 100))])
        self.assertEqual([], E.formularzeilen(t, w), "Feldbezeichnung nicht am Zeilenanfang")
        t, w = E.seitentext(zeilen_aus("Name: XYZ 123"))
        self.assertEqual([], E.formularzeilen(t, w), "Textebene: keine Formularzeilen")


class MarkierenVonHand(unittest.TestCase):
    def test_wort_an_punkt_und_bereich(self):
        w = ocr_zeile(("Erika", 10, 40), ("Mustermann", 50, 110))
        self.assertEqual(1, E.wort_an_punkt(w, 60, 105))
        self.assertIsNone(E.wort_an_punkt(w, 200, 105))
        self.assertEqual([0, 1], E.woerter_im_bereich(w, (0, 90, 120, 120)))
        self.assertEqual([1], E.woerter_im_bereich(w, (45, 90, 120, 120)))

    def test_unleserliche_seite(self):
        self.assertTrue(E.wirkt_unleserlich(ocr_zeile((";", 0, 5), ("g", 10, 15), ("8", 20, 25), ("2", 30, 35))))
        self.assertFalse(E.wirkt_unleserlich(ocr_zeile(("Sehr", 0, 20), ("geehrte", 25, 60), ("Frau", 65, 85))))

    def test_protokoll_nennt_markierungen(self):
        prot = E.pruefprotokoll(version="t", modell="m", zeitpunkt="z", original=b"a", export=b"b",
                                seiten_gesamt=1, quellen={0: "Textebene"}, funde={0: []},
                                gewaehlt=lambda p, f: True, balken=2, meldungen=[], von_hand=2)
        self.assertIn("von Hand markiert (Wörter und Bereiche): 2", prot)


if __name__ == "__main__":
    unittest.main()
