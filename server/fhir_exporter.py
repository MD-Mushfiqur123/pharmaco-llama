"""
HL7 FHIR (Fast Healthcare Interoperability Resources) R4 Exporter
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
Project: Pharmaco-Llama Autonomous Clinical OS
"""

import json
import uuid
import datetime
from typing import Dict, List, Optional, Tuple, Any

# Standard RxNorm mappings for common polypharmacy medications
RXNORM_CODEBOOK = {
    "warfarin": {"code": "855332", "display": "Warfarin Sodium 5 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "coumadin": {"code": "855332", "display": "Warfarin Sodium 5 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "clopidogrel": {"code": "309362", "display": "Clopidogrel 75 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "plavix": {"code": "309362", "display": "Clopidogrel 75 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "omeprazole": {"code": "312154", "display": "Omeprazole 20 MG Delayed Release Oral Capsule", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "prilosec": {"code": "312154", "display": "Omeprazole 20 MG Delayed Release Oral Capsule", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "pantoprazole": {"code": "284654", "display": "Pantoprazole 40 MG Delayed Release Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "protonix": {"code": "284654", "display": "Pantoprazole 40 MG Delayed Release Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "aspirin": {"code": "243670", "display": "Aspirin 81 MG Delayed Release Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "fluoxetine": {"code": "310385", "display": "Fluoxetine 20 MG Oral Capsule", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "prozac": {"code": "310385", "display": "Fluoxetine 20 MG Oral Capsule", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "linezolid": {"code": "311354", "display": "Linezolid 600 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "zyvox": {"code": "311354", "display": "Linezolid 600 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "lisinopril": {"code": "314076", "display": "Lisinopril 10 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "atorvastatin": {"code": "617314", "display": "Atorvastatin 40 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "metformin": {"code": "860975", "display": "Metformin hydrochloride 500 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "amlodipine": {"code": "197361", "display": "Amlodipine 5 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    "digoxin": {"code": "197604", "display": "Digoxin 0.125 MG Oral Tablet", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"}
}


def lookup_rxnorm(drug_name: str) -> Dict[str, str]:
    """Resolves medication name to RxNorm standard coding with fuzzy prefix fallback."""
    clean_name = drug_name.strip().lower()
    for key, coding in RXNORM_CODEBOOK.items():
        if key in clean_name:
            return coding
    
    # Generic unmapped coding
    hashed_id = str(abs(hash(clean_name)) % 1000000)
    return {
        "code": f"CUSTOM-{hashed_id}",
        "display": drug_name.title(),
        "system": "http://www.nlm.nih.gov/research/umls/rxnorm"
    }


class FHIRExporter:
    """
    HL7 FHIR R4 Bundle Exporter for Pharmaco-Llama.
    Constructs compliant Patient, MedicationStatement, DetectedIssue, and RiskAssessment resources.
    """

    def __init__(self, lead_scholar: str = "Md Mushfiqur Rahim, NIH Certified in Clinical Pharmacology & Clinical Research"):
        self.lead_scholar = lead_scholar

    def export_bundle(
        self,
        audit_result: Dict[str, Any],
        patient_info: Optional[Dict[str, Any]] = None,
        bundle_type: str = "collection"
    ) -> Dict[str, Any]:
        """
        Creates a complete FHIR R4 Bundle from audit results and patient demographics.
        """
        if patient_info is None:
            patient_info = {}

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        patient_id_raw = patient_info.get("patient_id", audit_result.get("patient_id", "PATIENT_9421"))
        patient_res_id = f"pat-{patient_id_raw.replace('_', '-').lower()}"
        bundle_id = f"bundle-audit-{uuid.uuid4().hex[:12]}"

        entries: List[Dict[str, Any]] = []

        # -------------------------------------------------------------------------
        # 1. Patient Resource
        # -------------------------------------------------------------------------
        patient_resource = self._build_patient_resource(
            patient_res_id=patient_res_id,
            patient_id_raw=patient_id_raw,
            patient_info=patient_info
        )
        entries.append({
            "fullUrl": f"urn:uuid:{uuid.uuid4()}",
            "resource": patient_resource
        })

        # -------------------------------------------------------------------------
        # 2. MedicationStatement Resources
        # -------------------------------------------------------------------------
        med_statements = []
        medications = patient_info.get("medications", audit_result.get("medications", []))
        
        # If medications is a list of strings or dicts
        for idx, med in enumerate(medications):
            if isinstance(med, dict):
                m_name = med.get("name", "Unknown Drug")
                m_dose = med.get("dose", "Standard")
            else:
                m_name = str(med)
                m_dose = "Standard"

            med_res_id = f"med-stmt-{idx + 1}-{uuid.uuid4().hex[:6]}"
            stmt = self._build_medication_statement(
                res_id=med_res_id,
                patient_ref=f"Patient/{patient_res_id}",
                drug_name=m_name,
                dose=m_dose,
                effective_date=now_iso
            )
            med_statements.append((med_res_id, m_name, stmt))
            entries.append({
                "fullUrl": f"urn:uuid:{uuid.uuid4()}",
                "resource": stmt
            })

        # -------------------------------------------------------------------------
        # 3. DetectedIssue Resources (One per clinical warning / hazard)
        # -------------------------------------------------------------------------
        warnings = audit_result.get("warnings", [])
        for idx, warn in enumerate(warnings):
            issue_res_id = f"issue-{idx + 1}-{uuid.uuid4().hex[:6]}"
            
            # Map evidence medications
            evidence_refs = []
            warn_msg = (warn.get("message", "") + " " + warn.get("type", "")).lower()
            for med_res_id, med_name, _ in med_statements:
                if med_name.lower().split()[0] in warn_msg:
                    evidence_refs.append({"reference": f"MedicationStatement/{med_res_id}"})
            
            # Fallback if specific medication reference wasn't linked
            if not evidence_refs and med_statements:
                evidence_refs.append({"reference": f"MedicationStatement/{med_statements[0][0]}"})

            issue_resource = self._build_detected_issue(
                res_id=issue_res_id,
                patient_ref=f"Patient/{patient_res_id}",
                warning=warn,
                identified_date=now_iso,
                evidence_refs=evidence_refs
            )
            entries.append({
                "fullUrl": f"urn:uuid:{uuid.uuid4()}",
                "resource": issue_resource
            })

        # -------------------------------------------------------------------------
        # 4. RiskAssessment Resource (Polypharmacy Hazard Index)
        # -------------------------------------------------------------------------
        hazard_score = audit_result.get("hazard_score", 15)
        risk_resource = self._build_risk_assessment(
            patient_ref=f"Patient/{patient_res_id}",
            hazard_score=hazard_score,
            audit_status=audit_result.get("audit_status", "NOMINAL"),
            occurrence_date=now_iso
        )
        entries.append({
            "fullUrl": f"urn:uuid:{uuid.uuid4()}",
            "resource": risk_resource
        })

        # -------------------------------------------------------------------------
        # Assemble FHIR Bundle
        # -------------------------------------------------------------------------
        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "versionId": "1.0",
                "lastUpdated": now_iso,
                "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"]
            },
            "identifier": {
                "system": "http://pharmaco-llama.org/fhir/audits",
                "value": audit_result.get("audit_id", f"AUD-{patient_id_raw}-{datetime.date.today().strftime('%Y%m%d')}")
            },
            "type": bundle_type,
            "timestamp": now_iso,
            "total": len(entries),
            "entry": entries
        }

        return bundle

    def _build_patient_resource(
        self,
        patient_res_id: str,
        patient_id_raw: str,
        patient_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Builds FHIR Patient Resource with renal and hepatic extensions."""
        age = patient_info.get("age", 68)
        sex = patient_info.get("sex", "male").lower()
        egfr = patient_info.get("egfr", 38.0)
        hepatic_status = patient_info.get("hepatic_status", "Child-Pugh Class B (Moderate Hepatic Impairment)")
        patient_name = patient_info.get("patient_name", f"Patient {patient_id_raw}")

        # Compute estimated birth year
        current_year = datetime.date.today().year
        birth_year = current_year - age

        extensions = [
            {
                "url": "http://pharmaco-llama.org/fhir/StructureDefinition/renal-egfr",
                "valueQuantity": {
                    "value": float(egfr),
                    "unit": "mL/min/1.73m2",
                    "system": "http://unitsofmeasure.org",
                    "code": "mL/min/1.73m2"
                }
            },
            {
                "url": "http://pharmaco-llama.org/fhir/StructureDefinition/hepatic-status",
                "valueString": hepatic_status
            },
            {
                "url": "http://pharmaco-llama.org/fhir/StructureDefinition/lead-pharmacologist",
                "valueString": self.lead_scholar
            }
        ]

        # Determine FHIR gender: male | female | other | unknown
        sex_clean = sex.strip().lower()
        if sex_clean.startswith("f"):
            fhir_gender = "female"
        elif sex_clean.startswith("m"):
            fhir_gender = "male"
        else:
            fhir_gender = "unknown"

        return {
            "resourceType": "Patient",
            "id": patient_res_id,
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
            },
            "identifier": [
                {
                    "use": "usual",
                    "system": "urn:oid:1.2.840.114350",
                    "value": patient_id_raw
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "text": patient_name,
                    "family": patient_name.split()[-1] if len(patient_name.split()) > 1 else patient_name,
                    "given": patient_name.split()[:-1] if len(patient_name.split()) > 1 else ["Unknown"]
                }
            ],
            "gender": fhir_gender,
            "birthDate": f"{birth_year}-01-01",
            "extension": extensions
        }

    def _build_medication_statement(
        self,
        res_id: str,
        patient_ref: str,
        drug_name: str,
        dose: str,
        effective_date: str
    ) -> Dict[str, Any]:
        """Builds FHIR MedicationStatement Resource."""
        rx_coding = lookup_rxnorm(drug_name)

        return {
            "resourceType": "MedicationStatement",
            "id": res_id,
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/MedicationStatement"]
            },
            "status": "active",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": rx_coding["system"],
                        "code": rx_coding["code"],
                        "display": rx_coding["display"]
                    }
                ],
                "text": f"{drug_name} ({dose})"
            },
            "subject": {
                "reference": patient_ref
            },
            "effectiveDateTime": effective_date,
            "dosage": [
                {
                    "text": dose,
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "260548002",
                                "display": "Oral"
                            }
                        ],
                        "text": "Oral route"
                    }
                }
            ]
        }

    def _build_detected_issue(
        self,
        res_id: str,
        patient_ref: str,
        warning: Dict[str, Any],
        identified_date: str,
        evidence_refs: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Builds FHIR DetectedIssue Resource with evidence linkage and mitigation."""
        raw_sev = warning.get("severity", "HIGH").upper()
        
        # HL7 FHIR DetectedIssue.severity value set: high | moderate | low
        if raw_sev in ["LETHAL", "CRITICAL"]:
            fhir_sev = "high"
        elif raw_sev in ["HIGH", "SEVERE"]:
            fhir_sev = "high"
        elif raw_sev in ["MODERATE", "MEDIUM"]:
            fhir_sev = "moderate"
        else:
            fhir_sev = "low"

        code_type = warning.get("type", "DRUG_INTERACTION")
        message = warning.get("message", "Potential drug-drug interaction detected.")
        recommendation = warning.get("recommendation", "Review regimen and monitor patient closely.")

        return {
            "resourceType": "DetectedIssue",
            "id": res_id,
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/DetectedIssue"]
            },
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "DRG",
                        "display": "Drug Interaction Alert"
                    }
                ],
                "text": code_type.replace("_", " ").title()
            },
            "severity": fhir_sev,
            "patient": {
                "reference": patient_ref
            },
            "identifiedDateTime": identified_date,
            "detail": message,
            "evidence": [
                {
                    "detail": evidence_refs
                }
            ],
            "mitigation": [
                {
                    "action": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                                "code": "ADMD",
                                "display": "Adjust Medication Dose"
                            }
                        ],
                        "text": recommendation
                    },
                    "date": identified_date,
                    "author": {
                        "display": self.lead_scholar
                    }
                }
            ]
        }

    def _build_risk_assessment(
        self,
        patient_ref: str,
        hazard_score: int,
        audit_status: str,
        occurrence_date: str
    ) -> Dict[str, Any]:
        """Builds FHIR RiskAssessment Resource representing Polypharmacy Hazard Index."""
        prob = min(1.0, max(0.0, float(round(hazard_score / 100.0, 3))))

        if hazard_score >= 80:
            qual_code = "high"
            qual_disp = "Critical / Severe Polypharmacy Hazard"
        elif hazard_score >= 50:
            qual_code = "moderate"
            qual_disp = "Moderate Polypharmacy Hazard"
        elif hazard_score >= 25:
            qual_code = "low"
            qual_disp = "Low Polypharmacy Hazard"
        else:
            qual_code = "negligible"
            qual_disp = "Negligible Hazard"

        return {
            "resourceType": "RiskAssessment",
            "id": f"risk-polypharmacy-{uuid.uuid4().hex[:6]}",
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/RiskAssessment"]
            },
            "status": "final",
            "subject": {
                "reference": patient_ref
            },
            "occurrenceDateTime": occurrence_date,
            "condition": {
                "text": "Adverse Polypharmacy Hazard & Metabolic Interference"
            },
            "prediction": [
                {
                    "outcome": {
                        "text": f"Hazard Score: {hazard_score}/100 [{audit_status}]"
                    },
                    "probabilityDecimal": prob,
                    "qualitativeRisk": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                                "code": qual_code,
                                "display": qual_disp
                            }
                        ],
                        "text": qual_disp
                    },
                    "rationale": f"Derived via Pharmaco-Llama PK Clearance & OpenFDA Boxed Warning Synthesis by {self.lead_scholar}"
                }
            ]
        }

    def validate_bundle(self, bundle: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates FHIR R4 Bundle compliance.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        if not isinstance(bundle, dict):
            return False, ["Bundle must be a JSON dictionary."]

        if bundle.get("resourceType") != "Bundle":
            errors.append(f"Root resourceType must be 'Bundle', found '{bundle.get('resourceType')}'")

        if "type" not in bundle:
            errors.append("Bundle missing required field 'type'")

        if "entry" not in bundle or not isinstance(bundle["entry"], list):
            errors.append("Bundle must contain an 'entry' array")
            return False, errors

        found_patient = False
        found_medication = False

        for idx, entry in enumerate(bundle["entry"]):
            if "resource" not in entry:
                errors.append(f"Entry {idx} missing 'resource' object")
                continue
            
            res = entry["resource"]
            res_type = res.get("resourceType")
            if not res_type:
                errors.append(f"Entry {idx} resource missing 'resourceType'")
                continue

            if res_type == "Patient":
                found_patient = True
                if "identifier" not in res:
                    errors.append(f"Patient resource {res.get('id')} missing identifier")
            elif res_type == "MedicationStatement":
                found_medication = True
                if "medicationCodeableConcept" not in res:
                    errors.append(f"MedicationStatement {res.get('id')} missing medicationCodeableConcept")
            elif res_type == "DetectedIssue":
                if "severity" not in res:
                    errors.append(f"DetectedIssue {res.get('id')} missing severity")
                if "detail" not in res:
                    errors.append(f"DetectedIssue {res.get('id')} missing detail")

        if not found_patient:
            errors.append("Bundle does not contain a Patient resource")
        if not found_medication:
            errors.append("Bundle does not contain any MedicationStatement resources")

        return len(errors) == 0, errors

    def to_json(self, bundle: Dict[str, Any], indent: int = 2) -> str:
        """Serializes bundle to indented JSON string."""
        return json.dumps(bundle, indent=indent, default=str)

    def export_to_file(self, bundle: Dict[str, Any], filepath: str, indent: int = 2) -> str:
        """Saves bundle to designated filepath."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=indent, default=str)
        return filepath


# Top-level functional convenience APIs
_default_exporter = FHIRExporter()

def export_fhir_bundle(audit_result: Dict[str, Any], patient_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _default_exporter.export_bundle(audit_result, patient_info)

def export_fhir_json(audit_result: Dict[str, Any], patient_info: Optional[Dict[str, Any]] = None, indent: int = 2) -> str:
    bundle = _default_exporter.export_bundle(audit_result, patient_info)
    return _default_exporter.to_json(bundle, indent=indent)

def validate_fhir_bundle(bundle: Dict[str, Any]) -> Tuple[bool, List[str]]:
    return _default_exporter.validate_bundle(bundle)
