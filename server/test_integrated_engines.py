"""
Unit and Integration Test Suite for the 5 Advanced Open-Source Scientific Frameworks:
1. PK-Sim PBPK Multi-Compartment ODE Simulation
2. Harvard & Stanford TDC TWOSIDES DDI Knowledge Base
3. DeepPurpose Molecular SMILES & Physicochemical Engine
4. comed NCBI PubMed Literature Evidence Mining
5. Donut/TrOCR Medical Prescription Parsing & Clinical NER
"""

import unittest
import numpy as np
import os
import sys

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)
PARENT_DIR = os.path.dirname(SERVER_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

try:
    from server.pbpk_engine import simulate_pbpk, PBPKVirtualPatient, pbpk_ode_system
    from server.tdc_ddi_engine import query_tdc_ddi, scan_full_regimen_tdc, TDC_DDI_KNOWLEDGE_BASE
    from server.molecular_engine import compute_smiles_descriptors, calculate_molecular_compatibility, CANONICAL_SMILES
    from server.pubmed_evidence import fetch_pubmed_evidence, OFFLINE_EVIDENCE_CACHE
    from server.vision_ocr_engine import parse_clinical_prescription_text
except ImportError:
    from pbpk_engine import simulate_pbpk, PBPKVirtualPatient, pbpk_ode_system
    from tdc_ddi_engine import query_tdc_ddi, scan_full_regimen_tdc, TDC_DDI_KNOWLEDGE_BASE
    from molecular_engine import compute_smiles_descriptors, calculate_molecular_compatibility, CANONICAL_SMILES
    from pubmed_evidence import fetch_pubmed_evidence, OFFLINE_EVIDENCE_CACHE
    from vision_ocr_engine import parse_clinical_prescription_text

class TestIntegratedScientificEngines(unittest.TestCase):

    # 1. PK-Sim PBPK Engine Tests
    def test_pbpk_simulation_execution(self):
        patient = PBPKVirtualPatient(age=70, weight_kg=75, egfr_ml_min=45)
        res = simulate_pbpk(
            dose_mg=20.0,
            ka=1.5,
            ke=0.04,
            vd_base=1.1,
            f_bioavailability=0.85,
            patient=patient,
            cyp_inhibition_factor=0.5
        )
        self.assertIn("c_plasma_mg_l", res)
        self.assertIn("c_liver_tissue_mg_l", res)
        self.assertIn("c_peripheral_mg_l", res)
        self.assertGreater(res["metrics"]["c_max_mg_l"], 0.0)
        self.assertGreater(res["metrics"]["auc_0_last"], 0.0)
        self.assertEqual(len(res["time_hours"]), 100)

    # 2. Harvard TDC DDI Tests
    def test_tdc_ddi_query_positive(self):
        match = query_tdc_ddi("Simvastatin", "Clarithromycin")
        self.assertIsNotNone(match)
        self.assertEqual(match["severity"], "CRITICAL_CONTRAINDICATION")
        self.assertIn("Rhabdomyolysis", match["twosides_adverse_event"])

    def test_tdc_regimen_scan(self):
        regimen = ["Warfarin", "Aspirin", "Amiodarone", "Metformin"]
        hits = scan_full_regimen_tdc(regimen)
        # Expect at least Warfarin+Aspirin and Warfarin+Amiodarone
        self.assertGreaterEqual(len(hits), 2)
        pairs = [f"{h['drug1']}+{h['drug2']}" for h in hits]
        self.assertTrue(any("Warfarin" in p and "Amiodarone" in p for p in pairs))

    # 3. DeepPurpose Molecular SMILES Tests
    def test_smiles_descriptors_calculation(self):
        warfarin_smiles = CANONICAL_SMILES["warfarin"]
        desc = compute_smiles_descriptors(warfarin_smiles)
        self.assertGreater(desc["approx_mw"], 250.0)
        self.assertGreater(desc["hba"], 0)
        self.assertIsInstance(desc["est_logp"], float)

    def test_molecular_compatibility_high_risk(self):
        res = calculate_molecular_compatibility("Simvastatin", "Amiodarone")
        self.assertEqual(res["status"], "COMPUTED")
        self.assertTrue(res["albumin_competition"])

    # 4. comed PubMed Evidence Tests
    def test_pubmed_evidence_retrieval(self):
        ev = fetch_pubmed_evidence("Warfarin", "Amiodarone")
        self.assertIn("evidence", ev)
        self.assertIn("pmid", ev["evidence"])
        self.assertEqual(ev["evidence"]["pmid"], "11980928")
        self.assertIn("pubmed.ncbi.nlm.nih.gov", ev["evidence"]["url"])

    # 5. Donut/TrOCR Clinical Prescription Parsing Tests
    def test_prescription_clinical_ner(self):
        rx_text = """
        Hospital Rx Clinic:
        Warfarin 5mg PO QD
        Amiodarone 200mg PO BID
        Simvastatin 20mg PO QHS
        """
        extracted = parse_clinical_prescription_text(rx_text)
        self.assertEqual(len(extracted), 3)
        names = [d["name"] for d in extracted]
        self.assertIn("Warfarin", names)
        self.assertIn("Amiodarone", names)
        self.assertIn("Simvastatin", names)
        self.assertEqual(extracted[0]["dose"], "5mg")
        self.assertEqual(extracted[1]["frequency"], "BID")

if __name__ == "__main__":
    unittest.main()
