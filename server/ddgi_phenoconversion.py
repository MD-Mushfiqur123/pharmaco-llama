"""
Pharmaco-Llama: DDGI (Drug-Drug-Gene Interaction) & Phenoconversion Calculator
Models Environmental/Inhibitor Burden Invalidating Genotypic Metabolizer Status
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

from typing import Dict, List, Any, Optional

# Known Potent Enzyme Inhibitors and their Activity Score Multipliers
INHIBITOR_PHENOCONVERSION_FACTORS: Dict[str, Dict[str, float]] = {
    "CYP2D6": {
        "fluoxetine": 0.0,      # Strong inhibitor -> complete phenoconversion to PM
        "paroxetine": 0.0,      # Strong inhibitor
        "bupropion": 0.1,       # Strong inhibitor
        "quinidine": 0.0,       # Strong inhibitor
        "duloxetine": 0.5,      # Moderate inhibitor
        "amiodarone": 0.5,      # Moderate inhibitor
        "sertraline": 0.6       # Moderate inhibitor at higher doses (>100mg)
    },
    "CYP2C19": {
        "omeprazole": 0.2,      # Potent competitive inhibitor
        "esomeprazole": 0.2,
        "fluconazole": 0.1,     # Dual CYP2C19/CYP3A4 inhibitor
        "fluvoxamine": 0.0      # Very potent inhibitor
    },
    "CYP3A4": {
        "clarithromycin": 0.05, # Suicide mechanism-based irreversible inhibitor
        "ketoconazole": 0.0,    # Very potent azole
        "itraconazole": 0.0,
        "ritonavir": 0.0,       # Booster / near-total CYP3A4 shutdown
        "diltiazem": 0.4,       # Moderate inhibitor
        "verapamil": 0.4
    },
    "CYP2C9": {
        "amiodarone": 0.3,      # Strong inhibitor of S-warfarin clearance
        "fluconazole": 0.2,     # Potent CYP2C9 inhibitor
        "metronidazole": 0.3    # Stereoselective inhibitor
    }
}

class PhenoconversionEngine:
    """
    Calculates effective enzymatic metabolizer status combining genetics with polypharmacy inhibitors.
    """
    def __init__(self):
        self.inhibitors = INHIBITOR_PHENOCONVERSION_FACTORS

    def calculate_effective_phenotype(
        self,
        gene: str,
        baseline_phenotype: str,
        co_medications: List[str]
    ) -> Dict[str, Any]:
        """
        Determines if concurrent drugs phenoconvert the patient from Normal to Intermediate or Poor metabolizer.
        """
        gene_upper = gene.strip().upper()
        gene_inhibitors = self.inhibitors.get(gene_upper, {})
        
        # Calculate baseline activity score
        baseline_score = 2.0
        if "poor" in baseline_phenotype.lower():
            baseline_score = 0.0
        elif "intermediate" in baseline_phenotype.lower():
            baseline_score = 1.0
        elif "ultrarapid" in baseline_phenotype.lower():
            baseline_score = 3.0
            
        current_multiplier = 1.0
        culprit_drugs = []
        
        for drug in co_medications:
            d_clean = drug.strip().lower()
            if d_clean in gene_inhibitors:
                factor = gene_inhibitors[d_clean]
                current_multiplier = min(current_multiplier, factor)
                culprit_drugs.append(d_clean.capitalize())
                
        effective_score = baseline_score * current_multiplier
        
        # Classify effective phenotype
        if effective_score < 0.25:
            effective_phenotype = "Phenoconverted Poor Metabolizer"
        elif effective_score < 1.25:
            effective_phenotype = "Phenoconverted Intermediate Metabolizer"
        elif effective_score <= 2.25:
            effective_phenotype = "Normal Metabolizer"
        else:
            effective_phenotype = "Ultrarapid Metabolizer"
            
        is_phenoconverted = (effective_phenotype != baseline_phenotype and len(culprit_drugs) > 0)
        
        return {
            "gene": gene_upper,
            "baseline_phenotype": baseline_phenotype,
            "baseline_activity_score": baseline_score,
            "effective_phenotype": effective_phenotype,
            "effective_activity_score": round(effective_score, 2),
            "is_phenoconverted": is_phenoconverted,
            "culprit_inhibitor_drugs": culprit_drugs,
            "clinical_warning": (
                f"PHENOCONVERSION DETECTED: Patient's genotypic status ({baseline_phenotype}) is invalidated by concurrent "
                f"{', '.join(culprit_drugs)}. Effective metabolic clearance matches a {effective_phenotype}."
            ) if is_phenoconverted else "Enzyme metabolic phenotype matches genotype."
        }
