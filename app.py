import streamlit as st
import fitz
from PIL import Image, ImageDraw
import io
import os
import json
import easyocr
import spacy
import numpy as np
import re

# --- 1. KONFIGURATION & MODELLE ---
st.set_page_config(page_title="Grauzone PRO", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['de', 'en'], gpu=True)

@st.cache_resource
def load_nlp():
    try:
        return spacy.load("de_core_news_lg")
    except OSError:
        return spacy.load("de_core_news_sm")

@st.cache_resource
def load_names_list():
    names_file = "vornamen.txt"
    if os.path.exists(names_file):
        with open(names_file, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    return set()

reader = load_ocr()
nlp = load_nlp()
NAME_DATABASE = load_names_list()
KNOWLEDGE_BASE = "knowledge_base.json"

# --- 2. HILFSFUNKTIONEN ---

def is_phone_number(text):
    clean_digits = re.sub(r"[^\d]", "", text)
    has_tel_format = bool(re.search(r"[\+\(\)\/\-]", text))
    if (has_tel_format and len(clean_digits) >= 5) or len(clean_digits) >= 8:
        return True
    return False

def analyze_text(text):
    lower_text = text.lower().strip()
    if is_phone_number(text):
        return True, "TEL"
    
    words = re.findall(r'\w+', lower_text)
    if any(word in NAME_DATABASE for word in words):
        return True, "DB_MATCH"

    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["PER", "LOC", "ORG"]:
            return True, ent.label_
    
    context_keywords = ["herr", "frau", "hallo", "liebe", "lieber", "geehrte", "tel", "mobil"]
    if any(kw in lower_text for kw in context_keywords) and len(words) > 0:
        return True, "CONTEXT_PII"
            
    return False, None

def load_knowledge():
    if os.path.exists(KNOWLEDGE_BASE):
        with open(KNOWLEDGE_BASE, "r", encoding="utf-8") as f: 
            return json.load(f)
    return {"whitelist": [], "blacklist": []}

def save_knowledge(data):
    with open(KNOWLEDGE_BASE, "w", encoding="utf-8") as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_pdf_page_image(doc, page_id, zoom):
    page = doc[page_id]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pix.tobytes()))

# --- 3. SESSION STATE ---
if 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = None
if 'results' not in st.session_state:
    st.session_state.results = []
if 'kb' not in st.session_state:
    st.session_state.kb = load_knowledge()

# --- 4. SIDEBAR (NAVIGATION & LERNFORTSCHRITT) ---
st.sidebar.title("🛡️ Grauzone PRO")

# Wissens-Monitor
with st.sidebar.expander("🧠 Lernfortschritt & Gedächtnis", expanded=False):
    col_bl, col_wl = st.columns(2)
    with col_bl:
        st.metric("Blacklist", len(st.session_state.kb["blacklist"]))
    with col_wl:
        st.metric("Whitelist", len(st.session_state.kb["whitelist"]))
    
    if st.button("Gedächtnis löschen", use_container_width=True):
        st.session_state.kb = {"whitelist": [], "blacklist": []}
        save_knowledge(st.session_state.kb)
        st.rerun()
    
    st.divider()
    if st.session_state.kb["blacklist"]:
        st.write("**Zuletzt gelernt (Blacklist):**")
        for item in list(st.session_state.kb["blacklist"])[-5:]:
            st.caption(f"• {item}")

uploaded_file = st.file_uploader("PDF Dokument hochladen", type="pdf")

# Reset-Logik bei neuer Datei
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.last_uploaded_file:
        st.session_state.results = []
        st.session_state.last_uploaded_file = uploaded_file.name
        st.rerun()

if uploaded_file:
    file_content = uploaded_file.read()
    doc = fitz.open(stream=file_content, filetype="pdf")
    
    p_id = st.sidebar.number_input("Seite", 0, len(doc)-1, 0)
    zoom_preview = st.sidebar.slider("Vorschau-Zoom", 0.5, 2.0, 1.0)
    current_img = get_pdf_page_image(doc, p_id, zoom_preview)

    col_view, col_ctrl = st.columns([2, 1])

    with col_ctrl:
        st.subheader("🕵️ Analyse")
        if st.button("🚀 SEITE SCANNEN", use_container_width=True):
            with st.spinner("Intensiv-Scan läuft..."):
                high_res_img = get_pdf_page_image(doc, p_id, 2.5)
                raw_results = reader.readtext(np.array(high_res_img.convert("RGB")))
                scale = zoom_preview / 2.5
                st.session_state.results = [([[p[0]*scale, p[1]*scale] for p in b], t, pr) for b, t, pr in raw_results]
                st.rerun()

        selected_items = []
        if st.session_state.results:
            st.write(f"**Ergebnisse Seite {p_id}:**")
            with st.container(height=500):
                for i, (bbox, text, prob) in enumerate(st.session_state.results):
                    clean_text = text.strip()
                    if len(clean_text) < 2: continue
                    
                    is_pii_ai, label = analyze_text(clean_text)
                    is_black = clean_text.lower() in [x.lower() for x in st.session_state.kb["blacklist"]]
                    is_white = clean_text.lower() in [x.lower() for x in st.session_state.kb["whitelist"]]
                    
                    check = (is_pii_ai or is_black) and not is_white
                    tag = f" [{label}]" if is_pii_ai else ""
                    
                    # Checkbox mit Lerneffekt
                    u_val = st.checkbox(f"{clean_text}{tag}", value=check, key=f"cb_{uploaded_file.name}_{p_id}_{i}")
                    
                    if u_val:
                        selected_items.append((bbox, clean_text))
                        # Lernen: Wenn User markiert, was die KI nicht wusste -> Blacklist
                        if u_val != check and clean_text not in st.session_state.kb["blacklist"]:
                            st.session_state.kb["blacklist"].append(clean_text)
                            save_knowledge(st.session_state.kb)
                    else:
                        # Lernen: Wenn User Markierung entfernt -> Whitelist
                        if u_val != check and clean_text not in st.session_state.kb["whitelist"]:
                            st.session_state.kb["whitelist"].append(clean_text)
                            save_knowledge(st.session_state.kb)

            if st.button("🔒 SCHWÄRZEN & EXPORT", type="primary", use_container_width=True):
                page = doc[p_id]
                img_w, img_h = current_img.size
                sc_x, sc_y = page.rect.width / img_w, page.rect.height / img_h
                for bbox, _ in selected_items:
                    x0, y0 = min([p[0] for p in bbox]) * sc_x, min([p[1] for p in bbox]) * sc_y
                    x1, y1 = max([p[0] for p in bbox]) * sc_x, max([p[1] for p in bbox]) * sc_y
                    page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(0,0,0))
                page.apply_redactions()
                output = io.BytesIO()
                doc.save(output)
                st.download_button("📥 PDF herunterladen", output.getvalue(), f"Anonymisiert_{uploaded_file.name}", use_container_width=True)

    with col_view:
        draw_img = current_img.copy()
        draw = ImageDraw.Draw(draw_img)
        for bbox, _ in selected_items:
            draw.polygon([tuple(p) for p in bbox], outline="red", width=3)
        st.image(draw_img, use_container_width=True, caption="Vorschau")