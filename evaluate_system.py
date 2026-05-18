import os
import json
import fitz
import easyocr
import spacy
import numpy as np
from PIL import Image
import io

TEST_DATA_DIR = "trainingsdaten"

print("Lade Modelle...")
reader = easyocr.Reader(['de', 'en'], gpu=True)
nlp = spacy.load("de_core_news_lg")

def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    return interArea > 0

def evaluate():
    if not os.path.exists(TEST_DATA_DIR):
        print("Ordner nicht gefunden.")
        return

    json_files = [f for f in os.listdir(TEST_DATA_DIR) if f.endswith('.json')]
    print(f"Gefundene Test-Datensätze: {len(json_files)}")
    
    total_expected = 0
    total_found = 0
    
    # Fortschrittszähler initialisieren
    for counter, json_file in enumerate(json_files, 1):
        base_name = json_file.replace('.json', '')
        pdf_path = os.path.join(TEST_DATA_DIR, f"{base_name}.pdf")
        
        with open(os.path.join(TEST_DATA_DIR, json_file), 'r') as f:
            ground_truth = json.load(f)
        
        total_expected += len(ground_truth)
        
        # PDF Scan
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img = Image.open(io.BytesIO(pix.tobytes()))
        results = reader.readtext(np.array(img))
        
        current_file_hits = 0
        matched_indices = set()
        
        for (bbox, text, prob) in results:
            pred_box = [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]]
            for i, gt in enumerate(ground_truth):
                if i not in matched_indices and calculate_iou(pred_box, gt['bbox']):
                    matched_indices.add(i)
                    current_file_hits += 1
        
        total_found += current_file_hits
        print(f"[{counter}/{len(json_files)}] {base_name}: {current_file_hits}/{len(ground_truth)} Treffer")

    recall = (total_found / total_expected) * 100 if total_expected > 0 else 0
    print(f"\n--- ERGEBNIS ---\nGesamt-Recall: {recall:.2f}%")

if __name__ == "__main__":
    evaluate()