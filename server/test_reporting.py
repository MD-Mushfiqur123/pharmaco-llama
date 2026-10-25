"""
Comprehensive Test Suite for Clinical Reporting & FHIR Export Engine
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
Project: Pharmaco-Llama Autonomous Clinical OS
"""

import os
import sys
import json
import unittest

# Ensure server module path is accessible
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from fhir_exporter import (
    FHIRExporter,
    export_fhir_bundle,
    export_fhir_json,
    validate_fhir_bundle,
    lookup_rxnorm
)
from report_generator import (
    ClinicalReportGenerator,
    generate_clinical_pdf
)


class TestFHIRR4Exporter(unittest.TestCase):
    """Rigorous validation of HL7 FHIR R4 Bundle schema & clinical resources."""

    def setUp(self):
        self.sample_audit = {
            "audit_id": "AUD-9421-TEST",
            "hazard_score": 94,
            "medication_count": 3,
            "audit_status": "FLAGGED_CRITICAL",
            "warnings": [
                {
                    "severity": "CRITICAL",
                    "type": "CYP2C19_BLOCKADE_AND_BLEEDING",
                    "message": "Omeprazole inhibits CYP2C19, preventing activation of Clopidogrel, while Warfarin + Antiplatelets create massive hemorrhage risk.",
                    "recommendation": "Discontinue Omeprazole; replace with Pantoprazole 40mg. Deprescribe redundant Aspirin."
                }
            ],
            "medications": [
                {"name": "Warfarin Sodium", "dose": "5mg Oral Daily"},
                {"name": "Clopidogrel Bisulfate", "dose": "75mg Oral Daily"},
                {"name": "Omeprazole", "dose": "20mg Oral Daily"}
            ]
        }
        self.patient_info = {
            "patient_id": "PATIENT_9421",
            "patient_name": "Eleanor Vance",
            "age": 72,
            "sex": "Female",
            "egfr": 34.5,
            "hepatic_status": "Child-Pugh Class B (Moderate Hepatic Impairment)"
        }

    def test_export_bundle_structure(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        self.assertEqual(bundle["resourceType"], "Bundle")
        self.assertEqual(bundle["type"], "collection")
        self.assertIn("entry", bundle)
        self.assertGreaterEqual(len(bundle["entry"]), 4)  # Patient + 3 Meds + 1 Issue + 1 RiskAssessment

    def test_bundle_validation_schema(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        is_valid, errors = validate_fhir_bundle(bundle)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_patient_resource_fields(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        patient_entries = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient"]
        self.assertEqual(len(patient_entries), 1)
        pat = patient_entries[0]
        self.assertEqual(pat["gender"], "female")
        self.assertEqual(pat["identifier"][0]["value"], "PATIENT_9421")
        
        # Verify clinical extensions
        ext_urls = [ext["url"] for ext in pat["extension"]]
        self.assertTrue(any("renal-egfr" in url for url in ext_urls))
        self.assertTrue(any("hepatic-status" in url for url in ext_urls))
        self.assertTrue(any("lead-pharmacologist" in url for url in ext_urls))

    def test_medication_statements_and_rxnorm(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        med_entries = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationStatement"]
        self.assertEqual(len(med_entries), 3)

        # Check RxNorm coding for Warfarin
        warfarin_stmt = next((m for m in med_entries if "warfarin" in m["medicationCodeableConcept"]["text"].lower()), None)
        self.assertIsNotNone(warfarin_stmt)
        coding = warfarin_stmt["medicationCodeableConcept"]["coding"][0]
        self.assertEqual(coding["code"], "855332")
        self.assertIn("Warfarin", coding["display"])

        # Check RxNorm coding for Clopidogrel
        clop_stmt = next((m for m in med_entries if "clopidogrel" in m["medicationCodeableConcept"]["text"].lower()), None)
        self.assertIsNotNone(clop_stmt)
        coding_clop = clop_stmt["medicationCodeableConcept"]["coding"][0]
        self.assertEqual(coding_clop["code"], "309362")

    def test_detected_issue_and_evidence_linkage(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        issue_entries = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "DetectedIssue"]
        self.assertEqual(len(issue_entries), 1)
        issue = issue_entries[0]
        self.assertEqual(issue["severity"], "high")
        self.assertIn("Omeprazole", issue["detail"])
        self.assertTrue(len(issue["evidence"]) > 0)
        self.assertTrue(len(issue["mitigation"]) > 0)
        self.assertIn("Mushfiqur", issue["mitigation"][0]["author"]["display"])

    def test_risk_assessment_resource(self):
        bundle = export_fhir_bundle(self.sample_audit, self.patient_info)
        risk_entries = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "RiskAssessment"]
        self.assertEqual(len(risk_entries), 1)
        risk = risk_entries[0]
        pred = risk["prediction"][0]
        self.assertEqual(pred["probabilityDecimal"], 0.94)
        self.assertEqual(pred["qualitativeRisk"]["coding"][0]["code"], "high")

    def test_json_serialization_roundtrip(self):
        json_str = export_fhir_json(self.sample_audit, self.patient_info)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["resourceType"], "Bundle")
        self.assertEqual(parsed["total"], len(parsed["entry"]))

    def test_custom_drug_rxnorm_fallback(self):
        coding = lookup_rxnorm("NovelExperimentalCompound-X")
        self.assertTrue(coding["code"].startswith("CUSTOM-"))
        self.assertIn("Novel", coding["display"])


class TestClinicalPDFGenerator(unittest.TestCase):
    """Validation of publication-quality Clinical Pharmacology Safety Audit PDF generator."""

    def setUp(self):
        self.sample_audit = {
            "audit_id": "AUD-TEST-9999",
            "hazard_score": 98,
            "audit_status": "FLAGGED_CRITICAL",
            "warnings": [
                {
                    "severity": "LETHAL",
                    "type": "SEROTONIN_SYNDROME",
                    "message": "Linezolid (MAOI) + Fluoxetine (SSRI) combination is strictly contraindicated.",
                    "recommendation": "Halt Linezolid immediately. Switch to Daptomycin or Vancomycin."
                }
            ],
            "medications": [
                {"name": "Fluoxetine", "dose": "20mg PO Daily"},
                {"name": "Linezolid", "dose": "600mg PO BID"},
                {"name": "Warfarin", "dose": "5mg PO Daily"}
            ]
        }
        self.patient_info = {
            "patient_id": "PATIENT_CRITICAL_01",
            "patient_name": "Arthur Pendelton",
            "age": 69,
            "sex": "Male",
            "egfr": 28.0,
            "hepatic_status": "Child-Pugh Class C (Severe Hepatic Impairment)"
        }
        self.output_pdf = os.path.join(SERVER_DIR, "test_output_generated.pdf")

    def tearDown(self):
        if os.path.exists(self.output_pdf):
            try:
                os.remove(self.output_pdf)
            except Exception:
                pass

    def test_pdf_generation_bytes(self):
        pdf_bytes = generate_clinical_pdf(self.sample_audit, self.patient_info)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 20000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Output must start with valid PDF header")

    def test_pdf_file_writing(self):
        pdf_bytes = generate_clinical_pdf(self.sample_audit, self.patient_info, output_path=self.output_pdf)
        self.assertTrue(os.path.exists(self.output_pdf))
        self.assertGreater(os.path.getsize(self.output_pdf), 20000)
        self.assertEqual(len(pdf_bytes), os.path.getsize(self.output_pdf))

    def test_pdf_low_risk_scenario(self):
        low_risk_audit = {
            "audit_id": "AUD-LOW-001",
            "hazard_score": 10,
            "audit_status": "NOMINAL",
            "warnings": [],
            "medications": [
                {"name": "Metformin", "dose": "500mg PO Daily"},
                {"name": "Atorvastatin", "dose": "20mg PO Daily"}
            ]
        }
        healthy_patient = {
            "patient_id": "PATIENT_HEALTHY",
            "patient_name": "Jane Miller",
            "age": 45,
            "sex": "Female",
            "egfr": 95.0,
            "hepatic_status": "Preserved Hepatic Function (Child-Pugh Class A)"
        }
        pdf_bytes = generate_clinical_pdf(low_risk_audit, healthy_patient)
        self.assertGreater(len(pdf_bytes), 15000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_hazard_gauge_bounds(self):
        generator = ClinicalReportGenerator()
        for score in [0, 25, 50, 75, 94, 100]:
            gauge = generator._draw_hazard_gauge(score, width=500, height=35)
            self.assertIsNotNone(gauge)
            self.assertEqual(gauge.width, 500)


class TestFullClinicalPipelineIntegration(unittest.TestCase):
    """End-to-end integration test connecting audit logic with FHIR and PDF export."""

    def test_integrated_regimen_to_fhir_and_pdf(self):
        from openfda_engine import query_offline_label
        from pk_math import simulate_warfarin_omeprazole_crisis

        # 1. Regimen definition
        medications = [
            {"name": "Warfarin", "dose": "5mg Daily"},
            {"name": "Clopidogrel", "dose": "75mg Daily"},
            {"name": "Omeprazole", "dose": "20mg Daily"}
        ]
        patient = {
            "patient_id": "INT_TEST_01",
            "patient_name": "Robert Langdon",
            "age": 63,
            "sex": "Male",
            "egfr": 42.0,
            "hepatic_status": "Child-Pugh Class B"
        }

        # 2. Simulate audit engine logic
        pk_sim = simulate_warfarin_omeprazole_crisis()
        audit_res = {
            "audit_id": "AUD-INT-001",
            "hazard_score": 94,
            "audit_status": "FLAGGED_CRITICAL",
            "warnings": [
                {
                    "severity": "CRITICAL",
                    "type": "CYP2C19_BLOCKADE_AND_BLEEDING",
                    "message": "Omeprazole inhibits CYP2C19, impeding Clopidogrel bioactivation.",
                    "recommendation": "Discontinue Omeprazole; replace with Pantoprazole 40mg."
                }
            ],
            "medications": medications,
            "pharmacokinetics": pk_sim
        }

        # 3. Export FHIR Bundle
        fhir_bundle = export_fhir_bundle(audit_res, patient)
        is_valid, errors = validate_fhir_bundle(fhir_bundle)
        self.assertTrue(is_valid, f"FHIR validation failed: {errors}")

        # 4. Export Clinical PDF
        pdf_bytes = generate_clinical_pdf(audit_res, patient)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 30000)

    def test_fastapi_export_endpoints(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        payload = {
            "patient_id": "TEST_API_01",
            "patient_name": "Eleanor Vance",
            "age": 72,
            "sex": "Female",
            "egfr": 34.5,
            "hepatic_status": "Child-Pugh Class B",
            "medications": [
                {"name": "Warfarin", "dose": "5mg daily"},
                {"name": "Clopidogrel", "dose": "75mg daily"},
                {"name": "Omeprazole", "dose": "20mg daily"}
            ]
        }

        # 1. Test PDF Export Endpoint
        pdf_res = client.post("/api/export/pdf", json=payload)
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers.get("content-type"), "application/pdf")
        self.assertTrue(pdf_res.content.startswith(b"%PDF-"))

        # 2. Test FHIR Export Endpoint
        fhir_res = client.post("/api/export/fhir", json=payload)
        self.assertEqual(fhir_res.status_code, 200)
        self.assertEqual(fhir_res.headers.get("content-type"), "application/fhir+json")
        bundle = fhir_res.json()
        self.assertEqual(bundle.get("resourceType"), "Bundle")
        self.assertGreaterEqual(bundle.get("total", 0), 4)


if __name__ == '__main__':
    unittest.main()
