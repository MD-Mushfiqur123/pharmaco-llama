"""
Pharmaco-Llama: DeepPurpose-Inspired Molecular SMILES & Structural Feature Engine
Predicts Physicochemical Competition, Albumin Binding Displacement & Toxicophore Alerts
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

from typing import Dict, Any, List, Optional
import math

# Curated canonical SMILES for essential pharmaceutical agents
CANONICAL_SMILES: Dict[str, str] = {
    "warfarin": "CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O",
    "amiodarone": "CCCCCC1=NC2=C(O1)C=C(C=C2)C(=O)C3=C(I)C=C(OCCN(CC)CC)C=C3I",
    "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "naproxen": "CC(C1=CC2=C(C=C1)C=C(C=C2)OC)C(=O)O",
    "lisinopril": "NCCCC[C@H](NC(=O)[C@H](CCC1=CC=CC=C1)N)C(=O)N2CCC[C@H]2C(=O)O",
    "spironolactone": "CC12CCC(=O)C=C1CCC3C2CCC4(C3)C(CC45CCC(=O)O5)SC(=O)C",
    "simvastatin": "CCC(C)(C)C(=O)OC1CC(C=C2C1C(C(C=C2)C)CCC3CC(CC(=O)O3)O)C",
    "clarithromycin": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O",
    "clopidogrel": "COC(=O)C(C1=CC=CC=C1Cl)N2CCC3=C(C2)C=CS3",
    "omeprazole": "CC1=CN=C(C(=C1OC)C)CS(=O)C2=NC3=C(N2)C=C(C=C3)OC",
    "digoxin": "CC1C(C(CC(O1)OC2C(C(CC(O2)OC3C(C(CC(O3)OC4CCC5(C(C4)CCC6C5CCC7(C6(CCC7C8=CC(=O)OC8)O)C)C)O)C)O)C)O)O",
    "fluoxetine": "CNCCC(C1=CC=CC=C1)OC2=CC=C(C=C2)C(F)(F)F",
    "tramadol": "CN(C)CC(C1CCCCC1(C2=CC(=CC=C2)OC)O)C",
    "azithromycin": "CCC1C(C(C(N(CC(C(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)C)O",
    "metformin": "CN(C)C(=N)N=C(N)N",
    "paracetamol": "CC(=O)NC1=CC=C(C=C1)O",
    "atorvastatin": "CC(C)C1=C(C(=C(N1CCC(CC(CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4"
}

# Empirical physicochemical property estimators derived from SMILES topology
def compute_smiles_descriptors(smiles: str) -> Dict[str, Any]:
    """
    Computes molecular weight estimate, atom counts, H-bond counts, and lipophilicity alerts from SMILES.
    """
    c_count = smiles.count("C") + smiles.count("c")
    n_count = smiles.count("N") + smiles.count("n")
    o_count = smiles.count("O") + smiles.count("o")
    f_count = smiles.count("F")
    cl_count = smiles.count("Cl")
    s_count = smiles.count("S") + smiles.count("s")
    i_count = smiles.count("I")
    
    # Approx Molecular Weight
    approx_mw = (c_count * 12.011) + (n_count * 14.007) + (o_count * 15.999) + \
                (f_count * 18.998) + (cl_count * 35.453) + (s_count * 32.065) + (i_count * 126.904)
    # Estimate H-atoms based on standard valency
    approx_h = max(2, int(approx_mw / 14.0))
    approx_mw += approx_h * 1.008
    
    # H-Bond Donors (OH, NH)
    hbd = smiles.count("O") + smiles.count("N") if "O" in smiles or "N" in smiles else 0
    # Refined HBD heuristics
    hbd = smiles.count("O[H]") + smiles.count("OH") + smiles.count("NH") + smiles.count("N[H]")
    if "O" in smiles and hbd == 0 and ("(=O)O" in smiles or "C1=CC=C(O)" in smiles):
        hbd = 1
        
    # H-Bond Acceptors (All O and N atoms)
    hba = o_count + n_count
    
    # Wildman-Crippen inspired LogP topological estimator
    est_logp = round((c_count * 0.20) + (cl_count * 0.55) + (i_count * 0.85) - (o_count * 0.35) - (n_count * 0.25), 2)
    
    # Substructure alert flags
    alerts = []
    if i_count >= 2:
        alerts.append("Di-Iodinated Aryl Core (Thyroid & CYP2C9 Potent Affinity)")
    if "C(=O)O" in smiles:
        alerts.append("Carboxylic Acid (Glucuronidation & Renal OAT Substrate)")
    if "S(=O)" in smiles or "S3" in smiles:
        alerts.append("Sulfur Heterocycle (P-gp / Transporter Affinity)")
    if f_count >= 3:
        alerts.append("Trifluoromethyl Group (Metabolic Stability & High Lipophilicity)")
    if "C(=O)OC" in smiles or "OC(=O)" in smiles:
        alerts.append("Ester Moiety (Plasma Esterase Cleavable)")
        
    return {
        "smiles": smiles,
        "approx_mw": round(approx_mw, 1),
        "est_logp": est_logp,
        "hbd": hbd,
        "hba": hba,
        "structural_alerts": alerts
    }

def calculate_molecular_compatibility(drug1: str, drug2: str) -> Dict[str, Any]:
    """
    Evaluates molecular structural competition between two drugs based on DeepPurpose features.
    """
    s1 = CANONICAL_SMILES.get(drug1.lower())
    s2 = CANONICAL_SMILES.get(drug2.lower())
    
    if not s1 or not s2:
        return {
            "status": "UNAVAILABLE",
            "message": f"SMILES data not cataloged for {drug1} or {drug2}"
        }
        
    d1 = compute_smiles_descriptors(s1)
    d2 = compute_smiles_descriptors(s2)
    
    # Plasma Albumin Competition Score (High LogP + Carboxylic Acid or High MW)
    albumin_competition = False
    if d1["est_logp"] > 2.0 and d2["est_logp"] > 2.0:
        albumin_competition = True
        
    # CYP3A4 Substrate/Inhibitor Steric Overlap
    steric_overlap = abs(d1["approx_mw"] - d2["approx_mw"]) < 150 and (d1["approx_mw"] > 300)
    
    risk_level = "LOW"
    rationale = "No severe physicochemical steric collision detected."
    
    if albumin_competition and steric_overlap:
        risk_level = "HIGH_COMPETITION"
        rationale = "Both molecules share high lipophilicity (LogP > 2.0) and bulky molecular volume, predicting competitive displacement from human serum albumin and hepatic binding pockets."
    elif albumin_competition:
        risk_level = "MODERATE_COMPETITION"
        rationale = "Dual lipophilic profiles indicate potential displacement in systemic plasma protein binding."
        
    return {
        "status": "COMPUTED",
        "drug1": {"name": drug1, "descriptors": d1},
        "drug2": {"name": drug2, "descriptors": d2},
        "albumin_competition": albumin_competition,
        "steric_overlap": steric_overlap,
        "structural_risk_level": risk_level,
        "molecular_rationale": rationale
    }
