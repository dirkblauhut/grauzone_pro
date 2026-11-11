"""Die Streamlit-Oberfläche startet ohne Fehler (headless über AppTest)."""
import os
import unittest

from hilfen import PROJEKT


class AppStart(unittest.TestCase):
    def test_app_startet(self):
        from streamlit.testing.v1 import AppTest
        alt = os.getcwd()
        os.chdir(PROJEKT)   # app.py liest VERSION, vornamen.txt und knowledge_base.json relativ
        try:
            at = AppTest.from_file(os.path.join(PROJEKT, "app.py"), default_timeout=120).run()
        finally:
            os.chdir(alt)
        self.assertEqual([], [str(e.value) for e in at.exception])
        self.assertTrue(at.sidebar.title[0].value.startswith("🛡️ Grauzone PRO"))


if __name__ == "__main__":
    unittest.main()
