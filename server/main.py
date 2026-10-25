"""
Pharmaco-Llama Core REST API Gateway
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

from fastapi import FastAPI, HTTPException, Body, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn

from pk_math import (
    one_compartment_oral_absorption,
    calculate_cyp_inhibition,
    calculate_half_life,
    simulate_warfarin_omeprazole_crisis,
    simulate_dynamic_regimen_pk
)
from openfda_engine import query_drug_label
from pharmacogenomics import PharmacogenomicsEngine, DrugDatabase
from report_generator import generate_clinical_pdf
from fhir_exporter import export_fhir_bundle, export_fhir_json
from ai_service import analyze_prescription_image, generate_dynamic_clinical_plan

# Scientific Open-Source Framework Integration (TDC, PK-Sim, DeepPurpose, comed, Donut)
from pbpk_engine import simulate_pbpk, PBPKVirtualPatient
from tdc_ddi_engine import scan_full_regimen_tdc, query_tdc_ddi
from molecular_engine import calculate_molecular_compatibility, compute_smiles_descriptors, CANONICAL_SMILES
from pubmed_evidence import fetch_pubmed_evidence
from vision_ocr_engine import parse_clinical_prescription_text

pgx_engine = PharmacogenomicsEngine()

app = FastAPI(
    title="Pharmaco-Llama Clinical API",
    description="Autonomous Clinical Pharmacology & Polypharmacy Safety Auditor for the Meta $1M Global Hackathon",
    version="1.0.0"
)

# CORS enabled for all origins (Cloudflare Pages, localhost, mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DrugItem(BaseModel):
    name: str
    dose: Optional[str] = "Standard"

class PolypharmacyAuditRequest(BaseModel):
    patient_id: Optional[str] = "PATIENT_9421"
    patient_name: Optional[str] = "Eleanor Vance"
    age: Optional[int] = 72
    sex: Optional[str] = "Female"
    egfr: Optional[float] = 34.5
    hepatic_status: Optional[str] = "Child-Pugh Class B (Moderate Hepatic Impairment)"
    medications: List[DrugItem]
    patient_genotype: Optional[Dict[str, str]] = None

class PgxAuditRequest(BaseModel):
    patient_id: Optional[str] = "PATIENT_9421"
    medications: List[str]
    patient_genotype: Dict[str, str]

class PkSimRequest(BaseModel):
    dose_mg: float = 5.0
    bioavailability_f: float = 1.0
    ka: float = 1.2
    ke: float = 0.0173
    vd_liters: float = 10.0
    inhibitor_conc_umol: Optional[float] = 15.0
    ki_umol: Optional[float] = 12.5

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Pharmaco-Llama Clinical OS",
        "version": "1.0.0",
        "fda_database": "OpenFDA Live Connected",
        "models": ["Llama-3.2-Vision", "Llama-3.3-70B"],
        "lead_developer": "Md Mushfiqur Rahim (NIH-Certified Clinical Pharmacology)"
    }

@app.get("/api/fda/label/{drug_name}")
def get_fda_label(drug_name: str):
    return query_drug_label(drug_name)

def evaluate_regimen_interactions(medications: List[DrugItem], db: DrugDatabase, egfr: float = 90.0):
    """
    Truthful Dynamic Multi-Drug & CYP Pharmacological Interaction Engine.
    Evaluates all pairwise combinations against the 60-drug database, enzyme affinities, and FDA warnings.
    """
    warnings = []
    hazard_score = 15
    fda_boxed_warnings = []
    
    # 1. Resolve drugs and query OpenFDA
    resolved = []
    for item in medications:
        clean_name = item.name.strip()
        drug_info = db.resolve_drug(clean_name)
        resolved.append({
            "item": item,
            "info": drug_info,
            "canonical": db.get_canonical_name(clean_name) or clean_name.lower()
        })
        
        # Query OpenFDA for boxed warnings
        try:
            fda_res = query_drug_label(clean_name)
            if fda_res and fda_res.get("boxed_warning"):
                for bw in fda_res["boxed_warning"]:
                    if bw and "No critical" not in bw:
                        fda_boxed_warnings.append({
                            "drug": clean_name.upper(),
                            "title": f"FDA BOXED WARNING: {clean_name.upper()}",
                            "text": bw[:250] + "..." if len(bw) > 250 else bw
                        })
        except Exception:
            pass

    # 2. Pairwise interaction analysis
    n = len(resolved)
    for i in range(n):
        for j in range(i + 1, n):
            d1 = resolved[i]
            d2 = resolved[j]
            name1 = d1["canonical"]
            name2 = d2["canonical"]
            info1 = d1["info"] or {}
            info2 = d2["info"] or {}
            class1 = info1.get("drug_class", "").lower()
            class2 = info2.get("drug_class", "").lower()
            
            # Serotonin Syndrome Check: MAOI (Linezolid, Phenelzine) + SSRI/SNRI/Tramadol
            is_maoi = "linezolid" in name1 or "linezolid" in name2 or "maoi" in class1 or "maoi" in class2
            is_serotonergic = any(s in name1 or s in name2 for s in ["fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram", "venlafaxine", "duloxetine", "tramadol"])
            if is_maoi and is_serotonergic:
                hazard_score = max(hazard_score, 98)
                warnings.append({
                    "severity": "LETHAL",
                    "type": "FATAL_SEROTONIN_SYNDROME",
                    "drug": f"{d1['item'].name} + {d2['item'].name}",
                    "message": "Coadministration of a monoamine oxidase inhibitor (Linezolid) with serotonergic agents precipitates fatal serotonin toxicity, hyperpyrexia, and autonomic collapse.",
                    "recommendation": "Halt Linezolid immediately. Initiate non-MAOI alternative (Daptomycin or Vancomycin) or observe strict 5-week washout."
                })

            # Antithrombotic Hemorrhage Synergy (Anticoagulant + Antiplatelet)
            is_anticoag1 = "anticoagulant" in class1 or any(a in name1 for a in ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin"])
            is_anticoag2 = "anticoagulant" in class2 or any(a in name2 for a in ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin"])
            is_antiplate1 = "antiplatelet" in class1 or any(p in name1 for p in ["aspirin", "clopidogrel", "ticagrelor", "prasugrel"])
            is_antiplate2 = "antiplatelet" in class2 or any(p in name2 for p in ["aspirin", "clopidogrel", "ticagrelor", "prasugrel"])
            
            if (is_anticoag1 and is_antiplate2) or (is_anticoag2 and is_antiplate1):
                hazard_score = max(hazard_score, 88)
                warnings.append({
                    "severity": "CRITICAL",
                    "type": "SYNERGISTIC_HEMORRHAGE_HAZARD",
                    "drug": f"{d1['item'].name} + {d2['item'].name}",
                    "message": "Concurrent anticoagulation and antiplatelet inhibition creates high synergistic gastrointestinal and intracranial bleeding liability.",
                    "recommendation": "Re-evaluate dual therapy indication. Deprescribe redundant antiplatelet if stable; maintain tight INR or anti-Xa monitoring."
                })

            # Opioid + Benzodiazepine (FDA Black Box)
            is_opioid1 = "opioid" in class1 or any(o in name1 for o in ["morphine", "oxycodone", "fentanyl", "tramadol", "hydrocodone"])
            is_opioid2 = "opioid" in class2 or any(o in name2 for o in ["morphine", "oxycodone", "fentanyl", "tramadol", "hydrocodone"])
            is_benzo1 = "benzodiazepine" in class1 or any(b in name1 for b in ["diazepam", "alprazolam", "lorazepam", "clonazepam"])
            is_benzo2 = "benzodiazepine" in class2 or any(b in name2 for b in ["diazepam", "alprazolam", "lorazepam", "clonazepam"])
            
            if (is_opioid1 and is_benzo2) or (is_opioid2 and is_benzo1):
                hazard_score = max(hazard_score, 92)
                warnings.append({
                    "severity": "CRITICAL",
                    "type": "CENTRAL_RESPIRATORY_DEPRESSION",
                    "drug": f"{d1['item'].name} + {d2['item'].name}",
                    "message": "FDA Black Box Contraindication: Combined opioid and benzodiazepine therapy induces profound sedation, hypoventilation, respiratory arrest, and coma.",
                    "recommendation": "Avoid combination. Taper benzodiazepine or co-prescribe Naloxone rescue protocol."
                })

            # Statin + Strong CYP3A4 inhibitor
            is_statin = any(s in name1 or s in name2 for s in ["simvastatin", "lovastatin", "atorvastatin"])
            is_cyp3a4_inhib = any(ci in name1 or ci in name2 for ci in ["clarithromycin", "erythromycin", "ketoconazole", "itraconazole", "amiodarone"])
            if is_statin and is_cyp3a4_inhib:
                hazard_score = max(hazard_score, 92)
                warnings.append({
                    "severity": "CRITICAL",
                    "type": "CYP3A4_STATIN_RHABDOMYOLYSIS",
                    "drug": f"{d1['item'].name} + {d2['item'].name}",
                    "message": "CYP3A4 blockade drastically elevates systemic statin AUC, triggering severe rhabdomyolysis and acute myoglobinuric kidney failure.",
                    "recommendation": "Hold statin during antimicrobial therapy or transition to non-CYP3A4 statin (Rosuvastatin or Pravastatin)."
                })

            # Clopidogrel + CYP2C19 Inhibitor (Omeprazole)
            if ("clopidogrel" in name1 and "omeprazole" in name2) or ("clopidogrel" in name2 and "omeprazole" in name1):
                hazard_score = max(hazard_score, 94)
                warnings.append({
                    "severity": "CRITICAL",
                    "type": "CYP2C19_PRODRUG_ACTIVATION_FAILURE",
                    "drug": "Clopidogrel + Omeprazole",
                    "message": "Omeprazole competitively inhibits CYP2C19, slashing Clopidogrel active metabolite by 45% and elevating acute stent thrombosis risk.",
                    "recommendation": "Discontinue Omeprazole immediately; substitute with Pantoprazole 40mg (negligible CYP2C19 inhibition)."
                })

            # Digoxin + P-gp Inhibitor
            is_digoxin = "digoxin" in name1 or "digoxin" in name2
            is_pgp = any(p in name1 or p in name2 for p in ["amiodarone", "verapamil", "clarithromycin", "quinidine"])
            if is_digoxin and is_pgp:
                hazard_score = max(hazard_score, 88)
                warnings.append({
                    "severity": "CRITICAL",
                    "type": "P_GLYCOPROTEIN_DIGOXIN_TOXICITY",
                    "drug": "Digoxin + P-gp Inhibitor",
                    "message": "P-glycoprotein efflux blockade reduces renal Digoxin clearance, precipitating AV block, lethal arrhythmias, and digitalis intoxication.",
                    "recommendation": "Empirically reduce Digoxin dose by 50% and monitor serum digoxin trough levels (<0.9 ng/mL)."
                })

            # Enzymatic conflict from drug database parameters
            enz1 = set([e.upper() for e in info1.get("primary_cyp_enzymes", [])])
            inhib2 = set([e.upper() for e in info2.get("inhibitors", [])])
            conflict12 = enz1.intersection(inhib2)
            if conflict12:
                hazard_score = max(hazard_score, 75)
                warnings.append({
                    "severity": "HIGH",
                    "type": f"CYP_INHIBITION_{list(conflict12)[0]}",
                    "drug": f"{d1['item'].name} (substrate) + {d2['item'].name} (inhibitor)",
                    "message": f"{d2['item'].name} inhibits {', '.join(conflict12)}, impeding the metabolic clearance of {d1['item'].name} and elevating plasma concentrations.",
                    "recommendation": f"Monitor for {d1['item'].name} toxicity; consider dose reduction or alternative agent."
                })

            enz2 = set([e.upper() for e in info2.get("primary_cyp_enzymes", [])])
            inhib1 = set([e.upper() for e in info1.get("inhibitors", [])])
            conflict21 = enz2.intersection(inhib1)
            if conflict21:
                hazard_score = max(hazard_score, 75)
                warnings.append({
                    "severity": "HIGH",
                    "type": f"CYP_INHIBITION_{list(conflict21)[0]}",
                    "drug": f"{d2['item'].name} (substrate) + {d1['item'].name} (inhibitor)",
                    "message": f"{d1['item'].name} inhibits {', '.join(conflict21)}, impeding the metabolic clearance of {d2['item'].name} and elevating plasma concentrations.",
                    "recommendation": f"Monitor for {d2['item'].name} toxicity; consider dose reduction or alternative agent."
                })

    # 3. Multi-drug Regimen Patterns (e.g. Hyperkalemia Triple Whammy)
    names_all = [d["canonical"] for d in resolved]
    has_raas = any(r in names_all for r in ["lisinopril", "losartan", "enalapril", "ramipril", "valsartan", "candesartan"])
    has_k_sparing = any(k in names_all for k in ["spironolactone", "eplerenone", "triamterene", "amiloride"])
    has_potassium = any("potassium" in n or "kcl" in n for n in names_all)
    has_nsaid = any(ns in names_all for ns in ["ibuprofen", "naproxen", "meloxicam", "celecoxib", "diclofenac", "indomethacin"])
    has_diuretic = any(di in names_all for di in ["furosemide", "hydrochlorothiazide", "chlorthalidone"]) or has_k_sparing
    
    if has_raas and has_k_sparing and has_potassium:
        hazard_score = max(hazard_score, 96)
        warnings.append({
            "severity": "LETHAL",
            "type": "MALIGNANT_HYPERKALEMIA_CARDIAC_ARREST",
            "drug": "RAAS Inhibitor + Spironolactone + Exogenous Potassium",
            "message": "Triple combination halts physiological potassium elimination, rapidly provoking hyperkalemia (>6.5 mEq/L) and lethal ventricular fibrillation.",
            "recommendation": "Deprescribe exogenous Potassium immediately. Check serum [K+] within 12-24 hours."
        })
    elif has_raas and has_k_sparing:
        hazard_score = max(hazard_score, 78)
        warnings.append({
            "severity": "HIGH",
            "type": "SYNERGISTIC_POTASSIUM_RETENTION",
            "drug": "ACEi/ARB + Aldosterone Antagonist",
            "message": "Dual blockade of aldosterone and angiotensin II elevates risk of hyperkalemia, particularly in patients with baseline renal impairment.",
            "recommendation": "Monitor serum electrolytes and creatinine at 1, 4, and 12 weeks."
        })

    # Triple Whammy: RAAS + Diuretic + NSAID
    if has_raas and has_diuretic and has_nsaid:
        hazard_score = max(hazard_score, 85)
        warnings.append({
            "severity": "HIGH",
            "type": "NEPHROTOXIC_TRIPLE_WHAMMY",
            "drug": "ACEi/ARB + Diuretic + NSAID",
            "message": "Concurrent afferent arteriolar constriction (NSAID), efferent dilation (ACEi), and volume depletion (diuretic) dramatically drops GFR, precipitating Acute Kidney Injury.",
            "recommendation": "Deprescribe NSAID; substitute with Acetaminophen or topical analgesic."
        })

    return warnings, hazard_score, fda_boxed_warnings

@app.post("/api/audit-regimen")
def audit_regimen(request: PolypharmacyAuditRequest):
    # 1. Truthful Dynamic Pairwise and Polypharmacy Evaluation
    warnings, hazard_score, fda_boxed_warnings = evaluate_regimen_interactions(
        request.medications, pgx_engine.db, egfr=request.egfr or 90.0
    )
        
    pgx_result = None
    if request.patient_genotype:
        pgx_result = pgx_engine.assess_patient_risk(
            request.patient_genotype, [d.name for d in request.medications]
        )
        hazard_score = max(hazard_score, pgx_result["overall_hazard_score"])
        for a in pgx_result["alerts"]:
            warnings.append({
                "severity": a["severity"],
                "type": f"PGX_{a['alert_type']}",
                "drug": a["drug"],
                "message": f"[{a['gene']} - {a['drug']}] {a['summary']}",
                "recommendation": a["recommendation"],
                "phenotype": a["phenotype"],
                "guideline": a["guideline_source"]
            })

    # 2. Truthful Dynamic Pharmacokinetic Simulation (Calculates real Cp(t) for ANY active drug)
    pk_data = simulate_dynamic_regimen_pk(
        request.medications, pgx_engine.db, egfr=request.egfr or 90.0
    )
    
    # 3. Real Generative AI Clinical Action Plan via Groq/Llama
    meds_dict = [{"name": d.name, "dose": getattr(d, "dose", "Standard")} for d in request.medications]
    ai_actions = generate_dynamic_clinical_plan(meds_dict, hazard_score, warnings, pk_data)

    # 4. Harvard TDC (Therapeutics Data Commons) TWOSIDES High-Scale DDI Scan
    med_names = [d.name for d in request.medications]
    tdc_hits = scan_full_regimen_tdc(med_names)

    # 5. PubMed NCBI Landmark & Live Medical Evidence (comed CoT paradigm)
    pubmed_citations = []
    if len(med_names) >= 2:
        for i in range(min(3, len(med_names))):
            for j in range(i + 1, min(4, len(med_names))):
                ev = fetch_pubmed_evidence(med_names[i], med_names[j])
                if ev and ev.get("evidence"):
                    pubmed_citations.append(ev)

    # 6. DeepPurpose-Inspired Molecular SMILES Physicochemical Feature Analysis
    molecular_evals = []
    if len(med_names) >= 2:
        for i in range(min(2, len(med_names))):
            for j in range(i + 1, min(3, len(med_names))):
                m_res = calculate_molecular_compatibility(med_names[i], med_names[j])
                if m_res.get("status") == "COMPUTED":
                    molecular_evals.append(m_res)

    return {
        "hazard_score": hazard_score,
        "medication_count": len(request.medications),
        "audit_status": "FLAGGED_CRITICAL" if hazard_score >= 80 else ("MAJOR_RISK" if hazard_score >= 50 else "NOMINAL"),
        "warnings": warnings,
        "fda_warnings": fda_boxed_warnings,
        "actions": ai_actions,
        "pharmacokinetics": pk_data,
        "pharmacogenomics": pgx_result,
        "tdc_ddi_hits": tdc_hits,
        "pubmed_citations": pubmed_citations,
        "molecular_evaluations": molecular_evals
    }

@app.post("/api/analyze-prescription")
async def analyze_prescription(file: UploadFile = File(...)):
    """
    Real Multimodal Vision Endpoint: Reads prescription/pill label image using Groq/Llama Vision API,
    extracts active drug entities, and audits the entire regimen.
    """
    try:
        image_bytes = await file.read()
        mime = file.content_type or "image/jpeg"
        extracted_drugs = analyze_prescription_image(image_bytes, mime)
        req = PolypharmacyAuditRequest(medications=[DrugItem(**d) for d in extracted_drugs])
        audit_result = audit_regimen(req)
        audit_result["extracted_medications"] = extracted_drugs
        audit_result["vision_status"] = "SUCCESS_NEURAL_OCR"
        return audit_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")

@app.get("/api/drugs")
def list_drugs():
    """Returns curated database of 50+ clinically vital medications."""
    drugs = pgx_engine.db.get_all_drugs()
    return {
        "total_count": len(drugs),
        "drugs": drugs
    }

@app.get("/api/drugs/{drug_name}")
def get_drug_details(drug_name: str):
    """Returns pharmacokinetic and PGx parameters for a specific drug."""
    drug = pgx_engine.db.resolve_drug(drug_name)
    if not drug:
        raise HTTPException(status_code=404, detail=f"Drug '{drug_name}' not found in database.")
    return drug

@app.post("/api/pgx/audit")
def audit_pgx(request: PgxAuditRequest):
    """High-risk pharmacogenomic risk assessment and phenoconversion calculator."""
    result = pgx_engine.assess_patient_risk(request.patient_genotype, request.medications)
    return {
        "patient_id": request.patient_id,
        "status": result["status"],
        "overall_hazard_score": result["overall_hazard_score"],
        "total_alerts": result["total_alerts"],
        "contraindicated_drugs": result["contraindicated_drugs"],
        "alerts": result["alerts"],
        "phenoconversion_events": result["phenoconversion_events"],
        "effective_phenotypes": result["effective_phenotypes"],
        "baseline_phenotypes": result["baseline_phenotypes"]
    }

@app.post("/api/simulate-pk")
def simulate_pk(request: PkSimRequest):
    times = [0, 2, 4, 8, 12, 18, 24, 36, 48, 60, 72]
    base_curve = one_compartment_oral_absorption(
        request.dose_mg, request.bioavailability_f, request.ka, request.ke, request.vd_liters, times
    )
    
    inhibited_ke, fold = calculate_cyp_inhibition(
        request.ke, request.inhibitor_conc_umol, request.ki_umol
    )
    
    inhibited_curve = one_compartment_oral_absorption(
        request.dose_mg, request.bioavailability_f, request.ka, inhibited_ke, request.vd_liters, times
    )
    
    return {
        "time_points_hours": times,
        "baseline_curve": base_curve,
        "inhibited_curve": inhibited_curve,
        "baseline_half_life_hours": calculate_half_life(request.ke),
        "inhibited_half_life_hours": calculate_half_life(inhibited_ke),
        "clearance_fold_reduction": fold
    }

@app.post("/api/export/pdf")
def export_pdf(request: PolypharmacyAuditRequest):
    """Generates official publication-quality Clinical Pharmacology Safety Audit PDF."""
    audit_data = audit_regimen(request)
    patient_info = {
        "patient_id": request.patient_id,
        "patient_name": request.patient_name,
        "age": request.age,
        "sex": request.sex,
        "egfr": request.egfr,
        "hepatic_status": request.hepatic_status,
        "medications": [{"name": m.name, "dose": m.dose} for m in request.medications]
    }
    pdf_bytes = generate_clinical_pdf(audit_data, patient_info)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=clinical_safety_audit_{request.patient_id}.pdf"
        }
    )

@app.post("/api/export/fhir")
def export_fhir(request: PolypharmacyAuditRequest):
    """Exports audit findings into HL7 FHIR R4 Bundle JSON."""
    audit_data = audit_regimen(request)
    patient_info = {
        "patient_id": request.patient_id,
        "patient_name": request.patient_name,
        "age": request.age,
        "sex": request.sex,
        "egfr": request.egfr,
        "hepatic_status": request.hepatic_status,
        "medications": [{"name": m.name, "dose": m.dose} for m in request.medications]
    }
    bundle = export_fhir_bundle(audit_data, patient_info)
    return Response(
        content=export_fhir_json(audit_data, patient_info),
        media_type="application/fhir+json",
        headers={
            "Content-Disposition": f"attachment; filename=fhir_bundle_{request.patient_id}.json"
        }
    )

# -------------------------------------------------------------
# 5 ADVANCED OPEN-SOURCE FRAMEWORK SCIENTIFIC ENDPOINTS
# -------------------------------------------------------------

class PBPKSimulationRequest(BaseModel):
    dose_mg: float = 10.0
    ka: float = 1.2
    ke: float = 0.05
    vd_base: float = 0.8
    f_bioavailability: float = 0.9
    age: float = 65.0
    weight_kg: float = 70.0
    height_cm: float = 170.0
    sex: str = "male"
    egfr: float = 60.0
    cyp_inhibition_factor: float = 1.0

class TDCDDIScanRequest(BaseModel):
    medications: List[str]

class MolecularCompatibilityRequest(BaseModel):
    drug1: str
    drug2: str

class TextPrescriptionRequest(BaseModel):
    text: str

@app.post("/api/pbpk/simulate")
def api_simulate_pbpk(req: PBPKSimulationRequest):
    """PK-Sim / OSP inspired multi-compartment PBPK ODE integration."""
    patient = PBPKVirtualPatient(
        age=req.age,
        weight_kg=req.weight_kg,
        height_cm=req.height_cm,
        sex=req.sex,
        egfr_ml_min=req.egfr
    )
    result = simulate_pbpk(
        dose_mg=req.dose_mg,
        ka=req.ka,
        ke=req.ke,
        vd_base=req.vd_base,
        f_bioavailability=req.f_bioavailability,
        patient=patient,
        cyp_inhibition_factor=req.cyp_inhibition_factor
    )
    return result

@app.post("/api/tdc/scan")
def api_scan_tdc(req: TDCDDIScanRequest):
    """Harvard & Stanford TDC (Therapeutics Data Commons) TWOSIDES DDI Scan."""
    hits = scan_full_regimen_tdc(req.medications)
    return {
        "status": "SUCCESS",
        "total_hits": len(hits),
        "interactions": hits
    }

@app.post("/api/molecular/compatibility")
def api_molecular_compatibility(req: MolecularCompatibilityRequest):
    """DeepPurpose-inspired molecular SMILES descriptor & steric overlap scorer."""
    return calculate_molecular_compatibility(req.drug1, req.drug2)

@app.get("/api/pubmed/evidence/{drug1}/{drug2}")
def api_pubmed_evidence(drug1: str, drug2: str):
    """comed-inspired live NCBI PubMed literature retrieval with PMID citations."""
    return fetch_pubmed_evidence(drug1, drug2)

@app.post("/api/ocr/parse-text")
def api_parse_prescription_text(req: TextPrescriptionRequest):
    """Donut/TrOCR clinical entity recognition on prescription text."""
    extracted = parse_clinical_prescription_text(req.text)
    return {
        "status": "SUCCESS",
        "extracted_medications": extracted
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
