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


# --- 4. SIDEBAR ---
st.sidebar.title(f"🛡️ {TITEL}")

# Selbst-Update der Mac-App (grauzone-update.sh liegt nur im Datenordner der App)
if os.path.exists("grauzone-update.sh"):
    SPERRE = ".keine-updatepruefung"
    # Fester key statt value=: sonst entstünde bei jeder Änderung ein neues
    # Widget und die Auswahl spränge zurück.
    if "update_pruefen" not in st.session_state:
        st.session_state.update_pruefen = not os.path.exists(SPERRE)
    pruefen = st.sidebar.toggle(
        "Beim Start nach neuen Versionen suchen", key="update_pruefen",
        help="Fragt beim Start von Grauzone bei GitHub nur die neueste Versionsnummer ab, "
             "keine Dokumentinhalte. Installiert wird erst nach Rückfrage im Terminalfenster.")
    if pruefen and os.path.exists(SPERRE):
        os.remove(SPERRE)
    elif not pruefen and not os.path.exists(SPERRE):
        open(SPERRE, "w").close()

with st.sidebar.expander("🧠 Lernfortschritt & Gedächtnis", expanded=False):
    col_bl, col_wl = st.columns(2)
    with col_bl:
        st.metric("Immer schwärzen", len(kb["blacklist"]))
    with col_wl:
        st.metric("Nie schwärzen", len(kb["whitelist"]))
    if st.button("Gedächtnis löschen", width="stretch"):
        st.session_state.kb = {"whitelist": [], "blacklist": []}
        save_knowledge(st.session_state.kb)
        st.rerun()
    st.divider()
    if kb["blacklist"]:
        st.write("**Zuletzt gelernt (immer schwärzen):**")
        for item in list(kb["blacklist"])[-5:]:
            st.caption(f"• {item}")
    if kb["whitelist"]:
        st.write("**Zuletzt gelernt (nie schwärzen):**")
        for item in list(kb["whitelist"])[-5:]:
            st.caption(f"• {item}")

if st.sidebar.button("⏻ Beenden", width="stretch",
                     help="Beendet Grauzone. Nicht heruntergeladene Ergebnisse gehen verloren."):
    # Erst die Meldung ausliefern, dann den Server kurz verzögert beenden
    threading.Timer(1.0, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
    st.info("**Grauzone wurde beendet.** Dieses Browserfenster und das Terminalfenster "
            "„Grauzone PRO“ können geschlossen werden. Zum erneuten Start Grauzone PRO neu öffnen.")
    st.stop()

uploaded_file = st.file_uploader("PDF Dokument hochladen", type="pdf")

if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded_file:
    st.session_state.last_uploaded_file = uploaded_file.name
    st.session_state.woerter = {}
    st.session_state.auswahl = {}
    st.session_state.export = None
    st.session_state.funde_speicher = {}
    st.session_state.seite = 1
    st.session_state.gezeigt = None
    st.rerun()


# --- 5. HILFSFUNKTIONEN FÜR DIE SEITE ---

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


def oeffne_pdf(daten):
    """Öffnet das PDF und übernimmt Formularfelder und Anmerkungen fest in die Seiten.

    apply_redactions() entfernt nur Seiteninhalt. Werte von Formularfeldern
    (z. B. "Name") und Anmerkungen (z. B. Notizen) liegen außerhalb davon und
    blieben sonst lesbar über den Balken stehen.
    """
    doc = pymupdf.open(stream=daten, filetype="pdf")
    for page in doc:
        for widget in page.widgets():
            try:
                widget.update()   # Darstellung aus dem Feldwert erzeugen, falls sie fehlt
            except Exception:
                pass
    doc.bake(annots=True, widgets=True)
    return doc


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


# --- 6. HAUPTBEREICH ---
if uploaded_file:
    file_content = uploaded_file.getvalue()
    doc = oeffne_pdf(file_content)
    n = len(doc)

    datei_id = (uploaded_file.name, len(file_content))
    if not 1 <= st.session_state.get("seite", 1) <= n:
        st.session_state.seite = 1
    p_id = st.sidebar.number_input(f"Seite (1–{n})", 1, n, key="seite") - 1
    alle_zeigen = st.sidebar.toggle(
        "Alle Seiten untereinander zeigen", value=n > 1,
        help="Die Vorschau zeigt alle Seiten zum Durchscrollen. Die Fundstellen-Liste "
             "rechts gehört zur gewählten Seite; wählen per „Bearbeiten“, Pfeilen oder Seitenzahl.")
    zoom_preview = st.sidebar.slider("Vorschau-Zoom", 0.5, 2.0, 1.0)
    ocr_erzwingen = st.sidebar.checkbox(
        "Immer Texterkennung (OCR) verwenden",
        help="Normalerweise liest Grauzone die Textebene des PDFs. Nur bei Scans ohne "
             "Textebene wird automatisch die Texterkennung genutzt. Einschalten, wenn ein "
             "PDF Text als Bild enthält (z. B. eingefügte Scans oder Stempel).")

    col_view, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.subheader("🕵️ Analyse")
        b1, b2 = st.columns(2)
        if b1.button("🚀 SEITE SCANNEN", width="stretch"):
            with st.spinner("Seite wird gelesen …"):
                scanne(doc, [p_id], ocr_erzwingen)
            st.rerun()
        if b2.button("📚 ALLE SEITEN", width="stretch"):
            with st.spinner(f"{n} Seiten werden gelesen …"):
                scanne(doc, range(n), ocr_erzwingen)
            st.rerun()

        funde = funde_der_seite(p_id)
        if p_id in st.session_state.woerter:
            quelle = st.session_state.woerter[p_id]["quelle"]
            st.write(f"**Fundstellen Seite {p_id + 1}** · {len(funde)} gefunden · gelesen per {quelle}")
            with st.container(height=420):
                if not funde:
                    st.caption("Keine personenbezogenen Daten erkannt.")
                for i, fund in enumerate(funde):
                    vorgabe = not in_liste(fund.text, kb["whitelist"])
                    wert = st.checkbox(
                        f"{fund.text}  ·  {E.ARTEN.get(fund.art, fund.art)}",
                        value=ist_gewaehlt(p_id, fund),
                        key=f"cb_{uploaded_file.name}_{p_id}_{i}_{fund.text}",
                    )
                    st.session_state.auswahl[(p_id, fund.text.lower())] = wert
                    # Lernen: abgewählt -> nie schwärzen; wieder gewählt -> Eintrag entfernen
                    if not wert and vorgabe and not in_liste(fund.text, kb["whitelist"]):
                        kb["whitelist"].append(fund.text)
                        save_knowledge(kb)
                    elif wert and not vorgabe:
                        kb["whitelist"] = [x for x in kb["whitelist"] if x.lower() != fund.text.lower()]
                        save_knowledge(kb)

            with st.form("zusatz", clear_on_submit=True):
                zusatz = st.text_input(
                    "Fehlt etwas? Begriff eingeben (mehrere mit Komma trennen)",
                    help="Der Begriff wird auf allen gescannten Seiten geschwärzt und für künftige Dokumente gemerkt.")
                if st.form_submit_button("➕ Hinzufügen", width="stretch") and zusatz.strip():
                    for begriff in [b.strip() for b in zusatz.split(",") if b.strip()]:
                        if not in_liste(begriff, kb["blacklist"]):
                            kb["blacklist"].append(begriff)
                        kb["whitelist"] = [x for x in kb["whitelist"] if x.lower() != begriff.lower()]
                    save_knowledge(kb)
                    st.session_state.export = None
                    st.rerun()
        else:
            st.caption("Diese Seite wurde noch nicht gescannt.")

        gescannt = sorted(st.session_state.woerter)
        if gescannt:
            offen = [str(p + 1) for p in range(n) if p not in st.session_state.woerter]
            if offen:
                st.warning(f"Nicht gescannt und daher **nicht geschwärzt**: Seite {', '.join(offen)}")
            if st.button("🔒 SCHWÄRZEN & EXPORT", type="primary", width="stretch"):
                out = oeffne_pdf(file_content)
                anzahl = 0
                for p in gescannt:
                    page = out[p]
                    for fund in funde_der_seite(p):
                        if ist_gewaehlt(p, fund):
                            for r in rechtecke(p, fund):
                                page.add_redact_annot(pymupdf.Rect(*r), fill=(0, 0, 0))
                                anzahl += 1
                    page.apply_redactions()
                E.bereinige_pdf(out)   # Autor, Titel, XMP, Lesezeichen, Anhänge entfernen
                puffer = io.BytesIO()
                out.save(puffer, garbage=4, deflate=True)
                meldungen = E.pruefe_export(puffer.getvalue(), {
                    p: [r for fund in funde_der_seite(p) if ist_gewaehlt(p, fund) for r in rechtecke(p, fund)]
                    for p in gescannt})
                md, _ = E.markdown(
                    [(p, st.session_state.woerter[p]["text"], funde_der_seite(p)) for p in gescannt],
                    ist_gewaehlt,
                    kopf=f"Erstellt mit {TITEL} am {date.today():%d.%m.%Y}. "
                         "Gleiche Angaben tragen denselben Platzhalter.",
                    nicht_gescannt=[p for p in range(n) if p not in st.session_state.woerter])
                st.session_state.export = (puffer.getvalue(), md, anzahl, len(gescannt), meldungen)
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
                d1.download_button("📥 PDF", daten, f"Anonymisiert_{name}.pdf",
                                   mime="application/pdf", width="stretch")
                d2.download_button("📝 Markdown", md.encode("utf-8"), f"Anonymisiert_{name}.md",
                                   mime="text/markdown", width="stretch",
                                   help="Text der gescannten Seiten; geschwärzte Stellen als Platzhalter "
                                        "wie [Person 1]. Tabellen und Layout bleiben nicht erhalten.")

    with col_view:
        # Blättern: Pfeile und Anzeige der gewählten Seite
        n1, n2, n3 = st.columns([1, 4, 1])
        n1.button("◀", on_click=gehe_zu, args=(p_id,), disabled=p_id == 0,
                  width="stretch", help="Vorige Seite")
        n2.markdown(f"<div style='text-align:center;padding-top:.4rem'><b>Seite {p_id + 1} von {n}</b></div>",
                    unsafe_allow_html=True)
        n3.button("▶", on_click=gehe_zu, args=(p_id + 2,), disabled=p_id == n - 1,
                  width="stretch", help="Nächste Seite")

        st.caption("Rot = wird geschwärzt, grau = abgewählt.")
        if alle_zeigen and n > 1:
            # Höhe an das Browserfenster anpassen, damit Pfeile und Seite gleichzeitig sichtbar bleiben
            st.markdown("<style>div:has(>.st-key-vorschau){--h:max(400px,calc(100vh - 340px));"
                        "height:var(--h)!important;flex:0 0 var(--h)!important}</style>",
                        unsafe_allow_html=True)
            with st.container(height=800, key="vorschau"):
                for p in range(n):
                    k1, k2 = st.columns([3, 1])
                    status = "gescannt" if p in st.session_state.woerter else "nicht gescannt"
                    k1.markdown(f"<span id='grauzone-seite-{p}'></span>"
                                f"**{'▶ ' if p == p_id else ''}Seite {p + 1}** · {status}",
                                unsafe_allow_html=True)
                    k2.button("Bearbeiten", key=f"bearbeiten_{p}", on_click=gehe_zu, args=(p + 1,),
                              disabled=p == p_id, width="stretch")
                    st.image(vorschau(doc, datei_id, p, zoom_preview), width="stretch")
            # Bei Seitenwechsel (Pfeile, Seitenzahl, Schalter) die Vorschau zur Seite scrollen
            if st.session_state.get("gezeigt") not in (None, (p_id, True)):
                zur_seite_scrollen(p_id)
            st.session_state.gezeigt = (p_id, True)
        else:
            st.image(vorschau(doc, datei_id, p_id, zoom_preview), width="stretch")
            st.session_state.gezeigt = (p_id, False)
