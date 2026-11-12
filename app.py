import io
import json
import os
import signal
import threading
from datetime import date

import easyocr
import pymupdf
import spacy
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

import erkennung as E

def lies_version():
    """Version aus VERSION (Mac-App: neben app.py) oder macos/VERSION (Quellcode)."""
    basis = os.path.dirname(os.path.abspath(__file__))
    for pfad in ("VERSION", os.path.join("macos", "VERSION")):
        try:
            with open(os.path.join(basis, pfad), encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    return ""


VERSION = lies_version()
TITEL = f"Grauzone PRO {VERSION}".strip()

# --- 1. KONFIGURATION & MODELLE ---
st.set_page_config(page_title=TITEL, layout="wide")


@st.cache_resource
def load_ocr():
    return easyocr.Reader(['de', 'en'], gpu=True, verbose=False)


@st.cache_resource
def load_nlp():
    for model_name in ["de_core_news_lg", "de_core_news_sm"]:
        try:
            return spacy.load(model_name)
        except OSError:
            continue
    raise RuntimeError(
        "Kein deutsches spaCy-Modell gefunden. Bitte Grauzone neu einrichten "
        "(Installationsprogramm erneut starten)."
    )


@st.cache_resource
def load_names_list():
    names_file = "vornamen.txt"
    if os.path.exists(names_file):
        with open(names_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    return set()


nlp = load_nlp()
NAME_DATABASE = load_names_list()
KNOWLEDGE_BASE = "knowledge_base.json"


# --- 2. WISSENSBASIS ---

def load_knowledge():
    if os.path.exists(KNOWLEDGE_BASE):
        with open(KNOWLEDGE_BASE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"whitelist": [], "blacklist": []}


def save_knowledge(data):
    with open(KNOWLEDGE_BASE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def in_liste(text, liste):
    return text.lower() in {x.lower() for x in liste}


# --- 3. SESSION STATE ---
for key, start in [("last_uploaded_file", None), ("woerter", {}), ("auswahl", {}), ("export", None)]:
    if key not in st.session_state:
        st.session_state[key] = start
if 'kb' not in st.session_state:
    st.session_state.kb = load_knowledge()
kb = st.session_state.kb


# --- 4. HILFSFUNKTIONEN FÜR DIE SEITE ---

def scanne(doc, seiten, ocr_erzwingen):
    """Holt die Wörter der Seiten (Textebene oder Texterkennung)."""
    for p in seiten:
        page = doc[p]
        zeilen = [] if ocr_erzwingen else E.woerter_aus_textebene(page)
        quelle = "Textebene"
        if sum(len(z) for z in zeilen) < 3:
            zeilen = E.woerter_aus_ocr(load_ocr(), page)
            quelle = "Texterkennung"
        text, woerter = E.seitentext(zeilen)
        st.session_state.woerter[p] = {"text": text, "woerter": woerter, "quelle": quelle}
    st.session_state.funde_speicher = {}
    st.session_state.export = None


def funde_der_seite(p):
    """Fundstellen einer gescannten Seite; zwischengespeichert, bis die Seite neu
    gescannt wird oder sich die Liste „immer schwärzen“ ändert."""
    daten = st.session_state.woerter.get(p)
    if not daten:
        return []
    schluessel = (p, id(daten), tuple(kb["blacklist"]))
    speicher = st.session_state.setdefault("funde_speicher", {})
    if schluessel not in speicher:
        speicher[schluessel] = E.finde(daten["text"], daten["woerter"], nlp, NAME_DATABASE, kb["blacklist"])
    return speicher[schluessel]


def ist_gewaehlt(p, fund):
    vorgabe = not in_liste(fund.text, kb["whitelist"])
    return st.session_state.auswahl.get((p, fund.text.lower()), vorgabe)


def rechtecke(p, fund):
    woerter = st.session_state.woerter[p]["woerter"]
    return [E.wort_rechteck(woerter[i], fund) for i in fund.woerter]


oeffne_pdf = E.oeffne_pdf   # Formularfelder und Anmerkungen fest in die Seite (siehe erkennung.py)


@st.cache_data(max_entries=300, show_spinner=False)
def seitenbild(_doc, datei_id, p, zoom):
    """Seite als Bild; zwischengespeichert je Datei, Seite und Zoom (datei_id ersetzt _doc als Schlüssel)."""
    pix = _doc[p].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def vorschau(doc, datei_id, p, zoom):
    """Seitenbild mit Markierungen: rot = wird geschwärzt, grau = abgewählt."""
    bild = seitenbild(doc, datei_id, p, zoom).copy()
    if p in st.session_state.woerter:
        draw = ImageDraw.Draw(bild, "RGBA")
        for fund in funde_der_seite(p):
            for x0, y0, x1, y1 in rechtecke(p, fund):
                box = [x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom]
                if ist_gewaehlt(p, fund):
                    draw.rectangle(box, fill=(220, 30, 30, 70), outline=(200, 0, 0, 255), width=2)
                else:
                    draw.rectangle(box, outline=(150, 150, 150, 255), width=1)
    return bild


def gehe_zu(seite):
    st.session_state.seite = seite


def zur_seite_scrollen(p):
    """Scrollt den Vorschau-Container, bis Seite p oben steht. Streamlit kann das
    nicht selbst; ein unsichtbares Skript sucht die Marke grauzone-seite-p in der
    Seite und wartet, bis alle Seitenbilder geladen sind (sonst stimmt die Höhe nicht)."""
    components.html(f"""<script>
    const d = window.parent.document, start = Date.now(), lauf = {st.session_state.get('scroll_nr', 0)};
    function versuch() {{
        const marke = d.getElementById("grauzone-seite-{p}");
        let box = marke && marke.parentElement;
        while (box && !(box.scrollHeight > box.clientHeight
                && /auto|scroll/.test(getComputedStyle(box).overflowY))) box = box.parentElement;
        const bilder = box ? [...box.querySelectorAll("img")] : [];
        const fertig = box && bilder.length && bilder.every(b => b.complete && b.naturalHeight);
        if (fertig) {{
            box.scrollTop += marke.getBoundingClientRect().top - box.getBoundingClientRect().top - 8;
        }} else if (Date.now() - start < 8000) {{
            setTimeout(versuch, 100);
        }}
    }}
    versuch();
    </script>""", height=0)
    st.session_state.scroll_nr = st.session_state.get("scroll_nr", 0) + 1


# --- 5. OBERFLÄCHE: Kopfzeile, drei Spalten (Dokument | Vorschau | Fundstellen) ---

STIL = """<style>
:root { --gz-navy:#0f2747; --gz-blau:#1d4ed8; --gz-rot:#d92d20; --gz-grau:#98a2b3;
        --gz-rand:#e4e7ec; --gz-text2:#667085; }
header[data-testid="stHeader"] { display:none; }
[data-testid="stMainBlockContainer"] { padding:0 1.2rem 3.2rem 1.2rem; max-width:none; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none; }
/* Kopfzeile */
.st-key-kopfzeile { background:var(--gz-navy); margin:-1rem -1.2rem .8rem -1.2rem; padding:.55rem 1.4rem; }
.st-key-kopfzeile [data-testid="stPopover"] button { background:transparent; color:#fff; border-color:#2a4f80; }
.gz-kopf { color:#fff; display:flex; align-items:center; gap:1rem; }
.gz-logo { font-size:1.6rem; line-height:1; }
.gz-name { font-size:1.35rem; font-weight:700; letter-spacing:.2px; }
.gz-name b { color:#7dd3fc; font-weight:700; }
.gz-claim { color:#cbd5e1; font-size:.9rem; border-left:1px solid #334e73; padding-left:1rem; }
.gz-rechts { margin-left:auto; display:flex; gap:.6rem; align-items:center; font-size:.85rem; }
.gz-badge { background:#16365f; border:1px solid #2a4f80; border-radius:999px; padding:.15rem .7rem; }
.gz-badge .punkt { color:#4ade80; }
.gz-test { background:#b45309; border-color:#d97706; }
/* Karten */
[class*="st-key-karte"] { background:#fff; border:1px solid var(--gz-rand) !important;
    border-radius:12px; box-shadow:0 1px 2px rgba(16,24,40,.05); }
.gz-titel { font-weight:650; font-size:.98rem; margin:0 0 .2rem 0; display:flex; gap:.45rem; align-items:center; }
.gz-klein { color:var(--gz-text2); font-size:.82rem; }
/* Hochladen als gestrichelte Fläche */
[data-testid="stFileUploaderDropzone"] { border:1.5px dashed #b6c2d9; background:#f8fafc; border-radius:10px; }
/* Fundstellen-Karten: rot = wird geschwärzt, grau = freigegeben */
[class*="st-key-fund_an"] { border-left:4px solid var(--gz-rot) !important; background:#fff; }
[class*="st-key-fund_aus"] { border-left:4px solid var(--gz-grau) !important; background:#f9fafb; }
[class*="st-key-fund_"] { border-radius:10px; }
.gz-art { display:inline-block; font-size:.75rem; color:var(--gz-text2); }
[class*="st-key-fund_"] { gap:0 !important; padding:.45rem .7rem !important; }
[class*="st-key-karte"] { gap:.55rem; }
[data-testid="stButtonGroup"] button { padding:.15rem .55rem; min-height:1.9rem; font-size:.8rem; }
.gz-zahl { font-size:1.35rem; font-weight:700; color:#101828; }
/* Werkzeugleiste über der Vorschau */
[class*="st-key-leiste"] { background:#fff; border:1px solid var(--gz-rand); border-radius:10px; padding:.25rem .4rem; }
.gz-mitte { text-align:center; padding-top:.45rem; font-size:.9rem; color:#344054; }
/* Legende unter der Vorschau */
.gz-legende { margin:.5rem auto 0 auto; width:max-content; background:#1f2937; color:#f3f4f6;
              border-radius:999px; padding:.25rem .9rem; font-size:.8rem; }
.gz-legende .rot { color:#f87171; } .gz-legende .grau { color:#9ca3af; }
/* Statuszeile unten */
.gz-status { position:fixed; left:0; right:0; bottom:0; z-index:100; background:#fff;
             border-top:1px solid var(--gz-rand); padding:.45rem 1.4rem; font-size:.85rem; color:#344054; }
.gz-status .ok { color:#16a34a; } .gz-status .warn { color:#b45309; }
</style>"""
st.markdown(STIL, unsafe_allow_html=True)

kopfzeile = st.container(key="kopfzeile")
kopf_l, kopf_b, kopf_r = kopfzeile.columns([11, 1.6, 1], vertical_alignment="center")
kopf_l.markdown(
    f"""<div class="gz-kopf"><span class="gz-logo">🛡️</span>
    <span class="gz-name">Grauzone <b>PRO</b></span>
    <span class="gz-claim">Personenbezogene Daten erkennen. Sicher schwärzen.</span>
    <span class="gz-rechts"><span class="gz-badge gz-test">Testversion</span>
    <span class="gz-badge"><span class="punkt">●</span> Lokal · v{VERSION}</span></span></div>""",
    unsafe_allow_html=True)
if kopf_b.button("⏻ Beenden", width="stretch",
                 help="Beendet Grauzone. Nicht heruntergeladene Ergebnisse gehen verloren."):
    # Erst die Meldung ausliefern, dann den Server kurz verzögert beenden
    threading.Timer(1.0, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
    st.info("**Grauzone wurde beendet.** Dieses Browserfenster und das Terminalfenster "
            "„Grauzone PRO“ können geschlossen werden. Zum erneuten Start Grauzone PRO neu öffnen.")
    st.stop()
with kopf_r.popover("⚙️", help="Einstellungen", width="stretch"):
    st.markdown("**Einstellungen**")
    # Selbst-Update der Mac-App (grauzone-update.sh liegt nur im Datenordner der App)
    if os.path.exists("grauzone-update.sh"):
        SPERRE = ".keine-updatepruefung"
        # Fester key statt value=: sonst entstünde bei jeder Änderung ein neues
        # Widget und die Auswahl spränge zurück.
        if "update_pruefen" not in st.session_state:
            st.session_state.update_pruefen = not os.path.exists(SPERRE)
        pruefen = st.toggle(
            "Beim Start nach neuen Versionen suchen", key="update_pruefen",
            help="Fragt beim Start von Grauzone bei GitHub nur die neueste Versionsnummer ab, "
                 "keine Dokumentinhalte. Installiert wird erst nach Rückfrage im Terminalfenster.")
        if pruefen and os.path.exists(SPERRE):
            os.remove(SPERRE)
        elif not pruefen and not os.path.exists(SPERRE):
            open(SPERRE, "w").close()
    st.caption("Alle Verarbeitung findet auf diesem Rechner statt. Es werden keine "
               "Dokumentinhalte übertragen.")

col_l, col_m, col_r = st.columns([1.05, 2.55, 1.45], gap="medium")


def titel(symbol, text, klein=""):
    zusatz = f"<span class='gz-klein'>{klein}</span>" if klein else ""
    st.markdown(f"<div class='gz-titel'>{symbol} {text} {zusatz}</div>", unsafe_allow_html=True)


# --- Linke Spalte: Hochladen, Dokument, Analyse, Lernfortschritt, Seitenübersicht ---
with col_l:
    karte_upload = st.container(border=True, key="karte_upload")
    with karte_upload:
        uploaded_file = st.file_uploader("PDF hochladen", type="pdf", label_visibility="collapsed",
                                         help="PDF hierher ziehen oder auswählen. Die Datei bleibt auf diesem Rechner.")

if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded_file:
    st.session_state.last_uploaded_file = uploaded_file.name
    st.session_state.woerter = {}
    st.session_state.auswahl = {}
    st.session_state.export = None
    st.session_state.funde_speicher = {}
    st.session_state.seite = 1
    st.session_state.gezeigt = None
    st.rerun()

if not uploaded_file:
    with col_l:
        with st.container(border=True, key="karte_lernen_leer"):
            titel("🧠", "Lernfortschritt")
            st.caption(f"{len(kb['blacklist'])} Begriffe immer schwärzen · "
                       f"{len(kb['whitelist'])} nie schwärzen")
    with col_m:
        with st.container(border=True, key="karte_leer"):
            st.markdown("### PDF hochladen, um zu beginnen")
            st.markdown(
                "1. Links ein PDF hochladen.\n"
                "2. **Alle Seiten scannen**: Grauzone sucht Namen, Anschriften, Telefonnummern, "
                "E-Mail-Adressen und IBANs.\n"
                "3. Rechts die Fundstellen prüfen: Haken = wird geschwärzt.\n"
                "4. **Schwärzen & exportieren**: PDF ohne die Daten und optional Markdown.")
            st.caption("Grauzone arbeitet vollständig lokal. Dokumente verlassen diesen Rechner nicht.")
    st.markdown("<div class='gz-status'>Bereit. Kein Dokument geladen.</div>", unsafe_allow_html=True)
    st.stop()

file_content = uploaded_file.getvalue()
doc = oeffne_pdf(file_content)
n = len(doc)
datei_id = (uploaded_file.name, len(file_content))
if not 1 <= st.session_state.get("seite", 1) <= n:
    st.session_state.seite = 1
for key, start in [("zoom", 1.0), ("alle_zeigen", n > 1), ("filter", "Alle")]:
    st.session_state.setdefault(key, start)
p_id = st.session_state.seite - 1


def haken_key(p, i, fund):
    return f"cb_{uploaded_file.name}_{p}_{i}_{fund.text}"


# Haken der Fundstellen-Liste übernehmen, bevor Vorschau und Zähler gezeichnet
# werden: Die Liste steht rechts und wird erst nach der Vorschau ausgeführt.
for i, fund in enumerate(funde_der_seite(p_id)):
    if haken_key(p_id, i, fund) in st.session_state:
        neu = st.session_state[haken_key(p_id, i, fund)]
        if st.session_state.auswahl.get((p_id, fund.text.lower())) != neu:
            st.session_state.auswahl[(p_id, fund.text.lower())] = neu
            st.session_state.export = None   # Export passt nicht mehr zur Auswahl


def zoom_aendern(schritt):
    st.session_state.zoom = min(2.0, max(0.5, round(st.session_state.zoom + schritt, 2)))


with col_l:
    with karte_upload:
        groesse = len(file_content) / 1024
        groesse = f"{groesse:.0f} KB" if groesse < 1024 else f"{groesse / 1024:.1f} MB"
        st.markdown(f"<span class='gz-klein'>📄 {groesse} · {n} Seite(n) · bleibt auf diesem Rechner</span>",
                    unsafe_allow_html=True)

    with st.container(border=True, key="karte_analyse"):
        titel("⚙️", "Analyse & Einstellungen")
        ocr_erzwingen = st.toggle(
            "Immer Texterkennung (OCR)",
            help="Normalerweise liest Grauzone die Textebene des PDFs. Nur bei Scans ohne "
                 "Textebene wird automatisch die Texterkennung genutzt. Einschalten, wenn ein "
                 "PDF Text als Bild enthält (z. B. eingefügte Scans oder Stempel).")
        if st.button("📚 Alle Seiten scannen", type="primary", width="stretch"):
            with st.spinner(f"{n} Seiten werden gelesen …"):
                scanne(doc, range(n), ocr_erzwingen)
            st.rerun()
        if st.button(f"🔍 Nur Seite {p_id + 1} scannen", width="stretch"):
            with st.spinner("Seite wird gelesen …"):
                scanne(doc, [p_id], ocr_erzwingen)
            st.rerun()

    with st.container(border=True, key="karte_lernen"):
        titel("🧠", "Lernfortschritt")
        m1, m2 = st.columns(2)
        m1.markdown(f"<span class='gz-zahl'>{len(kb['blacklist'])}</span><br>"
                    "<span class='gz-klein'>immer schwärzen</span>", unsafe_allow_html=True)
        m2.markdown(f"<span class='gz-zahl'>{len(kb['whitelist'])}</span><br>"
                    "<span class='gz-klein'>nie schwärzen</span>", unsafe_allow_html=True)
        with st.expander("Gelernte Begriffe"):
            if kb["blacklist"]:
                st.write("**Zuletzt gelernt (immer schwärzen):**")
                for item in list(kb["blacklist"])[-5:]:
                    st.caption(f"• {item}")
            if kb["whitelist"]:
                st.write("**Zuletzt gelernt (nie schwärzen):**")
                for item in list(kb["whitelist"])[-5:]:
                    st.caption(f"• {item}")
            if st.button("Gedächtnis löschen", width="stretch"):
                st.session_state.kb = {"whitelist": [], "blacklist": []}
                save_knowledge(st.session_state.kb)
                st.rerun()

    with st.container(border=True, key="karte_seiten"):
        titel("🗂️", "Seitenübersicht", f"· {len(st.session_state.woerter)} von {n} gescannt")
        with st.container(height=min(260, 140 * ((n + 2) // 3) + 10), border=False):
            for start in range(0, n, 3):
                spalten = st.columns(3)
                for p in range(start, min(start + 3, n)):
                    with spalten[p - start]:
                        st.image(seitenbild(doc, datei_id, p, 0.25), width="stretch")
                        zeichen = "✓ " if p in st.session_state.woerter else ""
                        st.button(f"{zeichen}{p + 1}", key=f"mini_{p}", on_click=gehe_zu, args=(p + 1,),
                                  type="primary" if p == p_id else "secondary", width="stretch")

# --- Mittlere Spalte: Werkzeugleiste und Vorschau ---
with col_m:
    with st.container(key="leiste"):
        w = st.columns([0.7, 1.1, 0.9, 0.7, 0.4, 0.7, 0.9, 0.7, 2.2], vertical_alignment="center")
        w[0].button("◀", on_click=gehe_zu, args=(p_id,), disabled=p_id == 0, help="Vorige Seite", width="stretch")
        w[1].number_input("Seite", 1, n, key="seite", label_visibility="collapsed")
        w[2].markdown(f"<div class='gz-mitte'>/ {n}</div>", unsafe_allow_html=True)
        w[3].button("▶", on_click=gehe_zu, args=(p_id + 2,), disabled=p_id == n - 1, help="Nächste Seite",
                    width="stretch")
        w[5].button("−", on_click=zoom_aendern, args=(-0.25,), disabled=st.session_state.zoom <= 0.5,
                    help="Verkleinern", width="stretch")
        w[6].markdown(f"<div class='gz-mitte'>{st.session_state.zoom:.0%}</div>", unsafe_allow_html=True)
        w[7].button("+", on_click=zoom_aendern, args=(0.25,), disabled=st.session_state.zoom >= 2.0,
                    help="Vergrößern", width="stretch")
        w[8].toggle("Alle Seiten", key="alle_zeigen", disabled=n == 1,
                    help="Alle Seiten untereinander zum Durchscrollen. Die Fundstellen rechts gehören "
                         "zur gewählten Seite; wählen per Pfeilen, Seitenzahl oder Seitenübersicht.")

    zoom = st.session_state.zoom
    aufloesung = 1.5 if zoom <= 1 else 2.5   # Pixel je PDF-Punkt; Anzeigegröße regelt der Zoom
    # Zoom: Seiten breiter als die Spalte darstellen, dann seitlich scrollbar
    st.markdown(f"<style>.st-key-vorschau [data-testid='stImage'] img, .st-key-einzeln [data-testid='stImage'] img"
                f"{{width:{zoom * 100:.0f}% !important;max-width:none !important;}}"
                ".st-key-vorschau,.st-key-einzeln{overflow-x:auto !important;}"
                "div:has(>.st-key-vorschau){--h:max(400px,calc(100vh - 230px));"
                "height:var(--h)!important;flex:0 0 var(--h)!important}</style>",
                unsafe_allow_html=True)
    if st.session_state.alle_zeigen and n > 1:
        with st.container(height=800, key="vorschau"):
            for p in range(n):
                k1, k2 = st.columns([3, 1], vertical_alignment="center")
                status = "gescannt" if p in st.session_state.woerter else "nicht gescannt"
                k1.markdown(f"<span id='grauzone-seite-{p}'></span>"
                            f"**{'▶ ' if p == p_id else ''}Seite {p + 1}** · <span class='gz-klein'>{status}</span>",
                            unsafe_allow_html=True)
                k2.button("Fundstellen", key=f"bearbeiten_{p}", on_click=gehe_zu, args=(p + 1,),
                          disabled=p == p_id, type="tertiary", width="stretch")
                st.image(vorschau(doc, datei_id, p, aufloesung), width="stretch")
        # Bei Seitenwechsel (Pfeile, Seitenzahl, Schalter) die Vorschau zur Seite scrollen
        if st.session_state.get("gezeigt") not in (None, (p_id, True)):
            zur_seite_scrollen(p_id)
        st.session_state.gezeigt = (p_id, True)
    else:
        with st.container(key="einzeln"):
            st.image(vorschau(doc, datei_id, p_id, aufloesung), width="stretch")
        st.session_state.gezeigt = (p_id, False)

    funde = funde_der_seite(p_id)
    aktiv = sum(ist_gewaehlt(p_id, f) for f in funde)
    st.markdown(f"<div class='gz-legende'>Seite {p_id + 1}: {len(funde)} Fundstellen · "
                f"<span class='rot'>●</span> {aktiv} wird geschwärzt · "
                f"<span class='grau'>●</span> {len(funde) - aktiv} freigegeben</div>",
                unsafe_allow_html=True)

# --- Rechte Spalte: Fundstellen-Analyse und Export ---
GRUPPEN = {"Alle": None, "Personen": {"PER"}, "Kontakte": {"TEL", "MAIL", "ADR"},
           "Weitere": {"ORT", "ORG", "IBAN", "LISTE"}}

with col_r:
    with st.container(border=True, key="karte_funde"):
        titel("📊", "Fundstellen-Analyse", f"· Seite {p_id + 1}")
        if p_id not in st.session_state.woerter:
            st.info("Diese Seite wurde noch nicht gescannt. Links **Alle Seiten scannen** wählen.")
        else:
            quelle = st.session_state.woerter[p_id]["quelle"]
            anzahl_je = {g: sum(1 for f in funde if arten is None or f.art in arten)
                         for g, arten in GRUPPEN.items()}
            gruppe = st.segmented_control(
                "Filter", list(GRUPPEN), key="filter", label_visibility="collapsed",
                format_func=lambda g: f"{g} ({anzahl_je[g]})") or "Alle"
            st.caption(f"gelesen per {quelle} · Haken = wird geschwärzt")
            with st.container(height=300, border=False):
                if not funde:
                    st.caption("Keine personenbezogenen Daten erkannt.")
                for i, fund in enumerate(funde):
                    if GRUPPEN[gruppe] is not None and fund.art not in GRUPPEN[gruppe]:
                        continue
                    vorgabe = not in_liste(fund.text, kb["whitelist"])
                    gewaehlt = ist_gewaehlt(p_id, fund)
                    with st.container(border=True, key=f"fund_{'an' if gewaehlt else 'aus'}_{p_id}_{i}"):
                        wert = st.checkbox(
                            f"**{fund.text}**",
                            value=gewaehlt,
                            key=haken_key(p_id, i, fund),
                        )
                        st.markdown(f"<span class='gz-art'>{i + 1} · {E.ARTEN.get(fund.art, fund.art)} · "
                                    f"Seite {p_id + 1}</span>", unsafe_allow_html=True)
                    st.session_state.auswahl[(p_id, fund.text.lower())] = wert
                    # Lernen: abgewählt -> nie schwärzen; wieder gewählt -> Eintrag entfernen
                    if not wert and vorgabe and not in_liste(fund.text, kb["whitelist"]):
                        kb["whitelist"].append(fund.text)
                        save_knowledge(kb)
                    elif wert and not vorgabe:
                        kb["whitelist"] = [x for x in kb["whitelist"] if x.lower() != fund.text.lower()]
                        save_knowledge(kb)

            with st.form("zusatz", clear_on_submit=True, border=False):
                zusatz = st.text_input(
                    "Fehlt etwas?", placeholder="Begriff eingeben, mehrere mit Komma",
                    help="Der Begriff wird auf allen gescannten Seiten geschwärzt und für künftige Dokumente gemerkt.")
                if st.form_submit_button("➕ Hinzufügen", width="stretch") and zusatz.strip():
                    for begriff in [b.strip() for b in zusatz.split(",") if b.strip()]:
                        if not in_liste(begriff, kb["blacklist"]):
                            kb["blacklist"].append(begriff)
                        kb["whitelist"] = [x for x in kb["whitelist"] if x.lower() != begriff.lower()]
                    save_knowledge(kb)
                    st.session_state.export = None
                    st.rerun()

    gescannt = sorted(st.session_state.woerter)
    offen = [str(p + 1) for p in range(n) if p not in st.session_state.woerter]
    with st.container(border=True, key="karte_export"):
        titel("📤", "Export")
        if not gescannt:
            st.caption("Erst nach dem Scannen möglich.")
        else:
            if offen:
                st.warning(f"Nicht gescannt und daher **nicht geschwärzt**: Seite {', '.join(offen)}")
            if st.button("🔒 Schwärzen & exportieren", type="primary", width="stretch"):
                zu_schwaerzen = {
                    p: [r for fund in funde_der_seite(p) if ist_gewaehlt(p, fund) for r in rechtecke(p, fund)]
                    for p in gescannt}
                pdf_daten, anzahl = E.schwaerze(file_content, zu_schwaerzen)
                meldungen = E.pruefe_export(pdf_daten, zu_schwaerzen)
                md, _ = E.markdown(
                    [(p, st.session_state.woerter[p]["text"], funde_der_seite(p)) for p in gescannt],
                    ist_gewaehlt,
                    kopf=f"Erstellt mit {TITEL} am {date.today():%d.%m.%Y}. "
                         "Gleiche Angaben tragen denselben Platzhalter.",
                    nicht_gescannt=[p for p in range(n) if p not in st.session_state.woerter])
                st.session_state.export = (pdf_daten, md, anzahl, len(gescannt), meldungen)
            if st.session_state.export:
                daten, md, anzahl, seiten, meldungen = st.session_state.export
                if meldungen:
                    st.error("**Exportprüfung nicht bestanden.** Das PDF vor der Weitergabe nicht verwenden, "
                             "sondern prüfen:\n\n" + "\n".join(f"- {m}" for m in meldungen))
                else:
                    st.success(f"{anzahl} Stellen auf {seiten} Seite(n) geschwärzt. "
                               "Exportprüfung bestanden (Text, Balken, Metadaten, Lesezeichen, Anhänge).")
                name = os.path.splitext(uploaded_file.name)[0]
                d1, d2 = st.columns(2)
                d1.download_button("📥 Geschwärztes PDF", daten, f"Anonymisiert_{name}.pdf",
                                   mime="application/pdf", width="stretch")
                d2.download_button("📝 Markdown", md.encode("utf-8"), f"Anonymisiert_{name}.md",
                                   mime="text/markdown", width="stretch",
                                   help="Text der gescannten Seiten; geschwärzte Stellen als Platzhalter "
                                        "wie [Person 1]. Tabellen und Layout bleiben nicht erhalten.")

# --- Statuszeile ---
if not gescannt:
    status = "Dokument geladen. Noch nicht gescannt."
else:
    gesamt = sum(len(funde_der_seite(p)) for p in gescannt)
    status = (f"<span class='ok'>✔</span> Analyse: {len(gescannt)} von {n} Seite(n) gescannt, "
              f"{gesamt} Fundstellen gefunden.")
    if offen:
        status += f" <span class='warn'>Nicht gescannt: Seite {', '.join(offen)}.</span>"
st.markdown(f"<div class='gz-status'>{status}</div>", unsafe_allow_html=True)
