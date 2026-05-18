1. Vision & Zielsetzung
Grauzone ist eine lokale Anwendung zur DSGVO-konformen Anonymisierung von PDF-Dokumenten. Sie wurde speziell für den Einsatz auf Apple Silicon (M2) Hardware entwickelt, um höchste Datensicherheit zu garantieren, ohne auf Cloud-Dienste angewiesen zu sein.

Zweck: Identifizierung und Schwärzung personenbezogener Daten (PII) gemäß Art. 4 DSGVO.

Besonderheit: Robuste Erkennung von Maschinenschrift, Handschrift und Text in komplexen technischen Plänen.

Prinzip: "Human-in-the-Loop" – Die KI schlägt vor, der Mensch entscheidet.

2. Technische Architektur
2.1 Stack & Frameworks

Frontend: Streamlit (Python-basiertes Web-Interface für lokale Ausführung).

PDF-Engine: PyMuPDF (fitz) (Hochperformante Bibliothek zum Rendern und physischen Schwärzen von PDF-Vektorebenen).

OCR-Layer: EasyOCR (Nutzt Deep Learning zur Erkennung von Text und Handschrift, optimiert für macOS Metal/MPS Beschleunigung).

Intelligence: Geplante Integration von Mistral-7B via MLX-lm für kontextbasierte PII-Klassifizierung.

2.2 Hardware-Optimierung (MacBook Air M2, 8GB RAM)

Unified Memory Management: Nutzung von st.cache_resource, um KI-Modelle nur einmal in den RAM zu laden.

Lazy Loading: PDF-Seiten werden einzeln gerendert, um den Arbeitsspeicher nicht durch große Dokumente zu fluten.

Quantisierung: Einsatz von 4-bit komprimierten Modellen zur Reduktion des Speicherbedarfs.

3. Kernfunktionen
3.1 Analyse-Workflow

PDF-Ingestion: Einlesen des Dokuments ohne Speicherung auf der Festplatte (In-Memory).

Visuelle Umsetzung: Umwandlung der PDF-Vektoren in Rasterbilder für die KI-Analyse.

PII-Detektion: Scan der Seite auf Textfragmente.

Validierung: Der Nutzer markiert über Checkboxen die finalen Schwärzungsziele.

3.2 Schwärzung & Export

Physische Redaktion: Im Gegensatz zu einfachen schwarzen Boxen über dem Text (die man wegkopieren könnte), nutzt Grauzone apply_redactions(). Dies entfernt den Textinhalt unwiderruflich aus der PDF-Struktur.

Revisionssicherheit: Automatische Generierung eines Zeitstempel-basierten Protokolls (.txt), das alle geschwärzten Begriffe auflistet.

4. Strategie für synthetische Daten & Training
Um die Erkennung von verzerrten Dokumenten und Plänen zu verbessern, ohne echte Klardaten zu nutzen, ist folgendes Vorgehen definiert:

Generator-Skript: Ein Python-Tool erstellt künstliche Dokumente mit zufälligen Layouts (Briefköpfe, Legenden von Bauplänen).

Handschrift-Simulation: Nutzung von Google Fonts (Handwriting) zur Simulation menschlicher Einträge.

Augmentation: Einsatz von Albumentations, um Scans zu simulieren (Rauschen, Drehung, Unschärfe).

Fine-Tuning: Einsatz von LoRA (Low-Rank Adaptation), um das Basismodell auf diese spezifischen Layouts zu spezialisieren, ohne die Hardware zu überlasten.

5. Zukunfts-Roadmap
[ ] Vollständige MLX-Integration: Ablösung der einfachen Textsuche durch ein echtes Sprachmodell (Mistral), das versteht, dass "Drosselweg 5" eine Adresse ist, auch ohne dass es explizit gesucht wurde.

[ ] Multi-Page Scan: Hintergrund-Prozessierung des gesamten Dokuments statt nur einzelner Seiten.

[ ] Auto-Kategorisierung: Automatisches Gruppieren von Funden in Kategorien wie "Namen", "Adressen", "Bankdaten".

6. Sicherheitshinweise
Lokaler Host: Die App läuft ausschließlich auf localhost. Kein ausgehender Netzwerkverkehr für die Datenverarbeitung.

Originalschutz: Die Ursprungsdatei wird im Programmcode nur lesend (read-only) geöffnet. Alle Änderungen erfolgen in einer Kopie im RAM.

Dokumenten-Status: Version 1.1 (Stabilisiert für M2)

Autor: Dein KI-Prompt-Engineer & User

Projekt: Grauzone