"""
Pharmaco-Llama: Medical Prescription Parsing & Clinical NER Engine
Inspired by Donut (Document Understanding Transformer) & Clinical TrOCR
Extracts Structured Drug Entities, Dosages, Sig Frequencies, and Routes from Prescription Text
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

import re
from typing import List, Dict, Any

# Clinical regex patterns for medication dosages and medical sig instructions
DOSAGE_PATTERN = re.compile(r'(\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|iu|units?|tablets?|capsules?|puffs?)\b)', re.IGNORECASE)
FREQUENCY_PATTERN = re.compile(r'\b(once daily|twice daily|thrice daily|bid|tid|qid|qd|qhs|prn|every \d+ hours|stat|daily)\b', re.IGNORECASE)
ROUTE_PATTERN = re.compile(r'\b(oral|po|iv|im|sublingual|sl|inhalation|topical|subcutaneous|sc)\b', re.IGNORECASE)

KNOWN_DRUGS_SET = {
    "warfarin", "amiodarone", "aspirin", "naproxen", "lisinopril", "spironolactone",
    "simvastatin", "clarithromycin", "amlodipine", "clopidogrel", "omeprazole",
    "digoxin", "fluoxetine", "tramadol", "azithromycin", "metformin", "paracetamol",
    "acetaminophen", "ibuprofen", "pantoprazole", "atorvastatin", "rosuvastatin",
    "furosemide", "hydrochlorothiazide", "metoprolol", "carvedilol", "losartan",
    "valsartan", "gabapentin", "pregabalin", "sertraline", "escitalopram", "citalopram"
}

def parse_clinical_prescription_text(text: str) -> List[Dict[str, Any]]:
    """
    Parses unstructured handwritten or OCR-extracted prescription text into structured clinical records.
    """
    extracted = []
    lines = text.split("\n")
    
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        words = re.findall(r'[a-zA-Z]+', cleaned_line.lower())
        detected_drug = None
        
        for w in words:
            if w in KNOWN_DRUGS_SET:
                detected_drug = w.capitalize()
                break
                
        if detected_drug:
            # Extract dose
            dose_match = DOSAGE_PATTERN.search(cleaned_line)
            dose_str = dose_match.group(1) if dose_match else "Standard clinical dose"
            
            # Extract frequency
            freq_match = FREQUENCY_PATTERN.search(cleaned_line)
            freq_str = freq_match.group(1).upper() if freq_match else "DAILY"
            
            # Extract route
            route_match = ROUTE_PATTERN.search(cleaned_line)
            route_str = route_match.group(1).upper() if route_match else "ORAL"
            
            extracted.append({
                "name": detected_drug,
                "dose": dose_str,
                "frequency": freq_str,
                "route": route_str,
                "raw_text": cleaned_line
            })
            
    return extracted
