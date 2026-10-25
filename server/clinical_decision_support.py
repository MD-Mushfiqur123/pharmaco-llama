"""
Pharmaco-Llama: Clinical Decision Support System (CDSS) & Geriatric Safety Rules
Implements AGS Beers Criteria (2023 Update) & Anticholinergic Cognitive Burden (ACB) Scale
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

from typing import Dict, List, Any, Optional

# Anticholinergic Cognitive Burden (ACB) Scale Definitions (1 = Mild, 2 = Moderate, 3 = Severe)
ACB_DRUG_SCALE: Dict[str, int] = {
    # Score 3 (Severe anticholinergic - high risk of confusion, falls, delirium)
    "amitriptyline": 3,
    "diphenhydramine": 3,
    "hydroxyzine": 3,
    "oxybutynin": 3,
    "paroxetine": 3,
    "chlorpheniramine": 3,
    "promethazine": 3,
    "scopolamine": 3,
    "clomipramine": 3,
    "doxepin": 3,
    
    # Score 2 (Moderate anticholinergic)
    "carbamazepine": 2,
    "cyclobenzaprine": 2,
    "loperamide": 2,
    "nortriptyline": 2,
    "olanzapine": 2,
    
    # Score 1 (Mild / Possible anticholinergic)
    "atenolol": 1,
    "captopril": 1,
    "furosemide": 1,
    "haloperidol": 1,
    "metoprolol": 1,
    "prednisone": 1,
    "ranitidine": 1,
    "warfarin": 1,
    "diazepam": 1,
    "lorazepam": 1
}

# AGS Beers Criteria 2023 Potentially Inappropriate Medications (PIMs) in Older Adults (Age >= 65)
BEERS_CRITERIA_PIMS: Dict[str, Dict[str, str]] = {
    "diazepam": {
        "rationale": "Long-acting benzodiazepines increase risk of cognitive impairment, delirium, falls, and motor vehicle accidents in older adults.",
        "recommendation": "Avoid. If treating insomnia/anxiety, utilize non-pharmacologic CBT-I or selective SSRI/melatonin agonists."
    },
    "diphenhydramine": {
        "rationale": "Potent anticholinergic; high risk of confusion, dry mouth, constipation, urinary retention, and acute delirium.",
        "recommendation": "Avoid as hypnotic or allergy treatment in older adults. Use second-generation non-sedating antihistamines (Cetirizine, Fexofenadine)."
    },
    "indomethacin": {
        "rationale": "Most central-nervous-system adverse effects among NSAIDs; high risk of GI bleed and acute renal injury.",
        "recommendation": "Avoid. Prefer topical NSAIDs or Acetaminophen."
    },
    "ketorolac": {
        "rationale": "High risk of peptic ulcer disease and GI bleeding even with short-term oral therapy.",
        "recommendation": "Avoid oral formulation. Limit parenteral administration to max 5 days."
    },
    "nitrofurantoin": {
        "rationale": "Potential for pulmonary toxicity, hepatotoxicity, and peripheral neuropathy; lacks efficacy in CrCl < 30 mL/min.",
        "recommendation": "Avoid in CrCl < 30 mL/min or for long-term bacterial suppression."
    },
    "glimepiride": {
        "rationale": "Long-duration sulfonylurea causing severe, prolonged hypoglycemia in elderly patients.",
        "recommendation": "Avoid. Prefer shorter-acting sulfonylurea (Glipizide) or DPP-4 inhibitors."
    }
}

class ClinicalDecisionSupportEngine:
    """
    Evaluates geriatric safety, anticholinergic cumulative burden, and organ-specific contraindications.
    """
    def __init__(self):
        self.acb_scale = ACB_DRUG_SCALE
        self.beers_pims = BEERS_CRITERIA_PIMS

    def calculate_anticholinergic_burden(self, medications: List[str]) -> Dict[str, Any]:
        """
        Calculates total ACB score. Score >= 3 is clinically correlated with increased risk of dementia and mortality.
        """
        total_score = 0
        contributing_drugs = []
        
        for drug in medications:
            d_clean = drug.strip().lower()
            if d_clean in self.acb_scale:
                score = self.acb_scale[d_clean]
                total_score += score
                contributing_drugs.append({"drug": drug, "score": score})
                
        risk_level = "LOW"
        clinical_advice = "Nominal anticholinergic exposure."
        if total_score >= 3:
            risk_level = "HIGH_COGNITIVE_RISK"
            clinical_advice = "Total ACB score >= 3 is strongly associated with cognitive decline, acute delirium, and 30-day fall risk. Review regimen for deprescribing."
        elif total_score >= 1:
            risk_level = "MODERATE_EXPOSURE"
            clinical_advice = "Mild anticholinergic burden. Monitor for dry mouth, constipation, or sedation."
            
        return {
            "total_acb_score": total_score,
            "risk_level": risk_level,
            "clinical_advice": clinical_advice,
            "contributing_medications": contributing_drugs
        }

    def evaluate_geriatric_beers(self, age: int, medications: List[str]) -> List[Dict[str, Any]]:
        """
        Evaluates regimen against AGS Beers Criteria 2023 for older patients (Age >= 65).
        """
        if age < 65:
            return []
            
        flagged_pims = []
        for drug in medications:
            d_clean = drug.strip().lower()
            if d_clean in self.beers_pims:
                pim_data = self.beers_pims[d_clean]
                flagged_pims.append({
                    "drug": drug,
                    "criteria": "AGS Beers Criteria (2023)",
                    "rationale": pim_data["rationale"],
                    "recommendation": pim_data["recommendation"]
                })
        return flagged_pims

    def evaluate_renal_appropriateness(self, egfr: float, medications: List[str]) -> List[Dict[str, Any]]:
        """
        Identifies drugs requiring critical dose reduction or contraindication at patient's renal function level.
        """
        renal_alerts = []
        for drug in medications:
            d_clean = drug.strip().lower()
            if "metformin" in d_clean and egfr < 30.0:
                renal_alerts.append({
                    "drug": drug,
                    "level": "CONTRAINDICATED",
                    "reason": f"Metformin is contraindicated when eGFR < 30 mL/min/1.73m2 due to high risk of fatal lactic acidosis."
                })
            elif "metformin" in d_clean and egfr < 45.0:
                renal_alerts.append({
                    "drug": drug,
                    "level": "DOSE_REDUCTION",
                    "reason": f"eGFR 30-44 mL/min: Limit Metformin to max 1,000 mg/day; monitor renal markers every 3 months."
                })
            elif "spironolactone" in d_clean and egfr < 30.0:
                renal_alerts.append({
                    "drug": drug,
                    "level": "CONTRAINDICATED",
                    "reason": "Avoid Spironolactone when eGFR < 30 mL/min due to life-threatening hyperkalemia risk."
                })
            elif any(nsaid in d_clean for nsaid in ["ibuprofen", "naproxen", "ketorolac", "indomethacin"]) and egfr < 30.0:
                renal_alerts.append({
                    "drug": drug,
                    "level": "CONTRAINDICATED",
                    "reason": "Systemic NSAIDs cause renal afferent vasoconstriction, exacerbating chronic kidney disease to acute dialysis-requiring failure."
                })
        return renal_alerts
