import os
import json
import random
import time
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from faker import Faker

fake = Faker('de_DE')
OUTPUT_DIR = "trainingsdaten"

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)

def create_varied_pdf(index):
    timestamp = int(time.time() * 1000)
    file_id = f"test_{index}_{timestamp}"
    pdf_path = os.path.join(OUTPUT_DIR, f"{file_id}.pdf")
    json_path = os.path.join(OUTPUT_DIR, f"{file_id}.json")
    
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    ground_truth = []
    
    def write_pii(text, x, y, font_size=11):
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(x, y, text)
        text_width = len(text) * (font_size * 0.55)
        # Speichert die Bbox für den Abgleich
        ground_truth.append({
            "text": text,
            "bbox": [x * 2, (height-y-font_size) * 2, (x + text_width) * 2, (height-y) * 2]
        })

    y = height - 80
    
    # --- VARIATION DER ANREDEN ---
    last_name = fake.last_name()
    first_name = fake.first_name()
    
    # Verschiedene Varianten, wie Namen im Text vorkommen
    salutations = [
        f"Sehr geehrter Herr {last_name}",
        f"Liebe Frau {last_name}",
        f"Hallo {first_name}",
        f"Guten Tag {first_name} {last_name}",
        f"An {first_name} {last_name}"
    ]
    
    chosen_salutation = random.choice(salutations)
    
    # Brief-Szenario mit Fokus auf Kontext-Namen
    c.setFont("Helvetica", 11)
    write_pii(chosen_salutation, 50, y) # Die ganze Anrede als PII markieren
    
    c.drawString(50, y-40, "vielen Dank für Ihre Nachricht.")
    c.drawString(50, y-60, f"Wir haben die Unterlagen für {first_name} erhalten.")
    write_pii(first_name, 195, y-60) # Name im Fließtext
    
    # Telefonnummer dazu
    phone = fake.phone_number()
    c.drawString(50, y-100, "Für Rückfragen erreichen Sie uns unter:")
    write_pii(phone, 50, y-120)

    c.save()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=4)
    return file_id

for i in range(15):
    create_varied_pdf(i)
print(f"✅ 15 Testdateien mit Kontext-Anreden (Herr/Frau/Hallo) erstellt.")