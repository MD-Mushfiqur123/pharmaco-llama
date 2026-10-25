"""
Unit Test Suite for Pharmaco-Llama Pharmacogenomics Engine & Clinical Drug Database
Author: Lead Pharmacogenomics & Clinical Database Engineer
"""

import unittest
import os
import json

from pharmacogenomics import (
    PharmacogenomicsEngine,
    DrugDatabase,
    AlleleRegistry,
    MetabolizerPhenotype,
    PGxSeverity
)


class TestDrugDatabase(unittest.TestCase):
    """Validates completeness, validity, and physiological realism of drug_database.json."""

    @classmethod
    def setUpClass(cls):
        cls.db = DrugDatabase()
        cls.drugs = cls.db.get_all_drugs()

    def test_database_size_exceeds_fifty(self):
        self.assertGreaterEqual(len(self.drugs), 50, f"Expected at least 50 drugs, got {len(self.drugs)}")

    def test_required_fields_present_in_all_drugs(self):
        required_fields = [
            "generic_name",
            "brand_names",
            "drug_class",
            "therapeutic_area",
            "bioavailability_f",
            "ka",
            "ke",
            "vd_liters_per_kg",
            "half_life_hours",
            "primary_cyp_enzymes",
            "inhibitors",
            "inducers",
            "narrow_therapeutic_index",
            "high_risk_pgx_genes"
        ]

        for drug_key, details in self.drugs.items():
            for f in required_fields:
                self.assertIn(f, details, f"Drug '{drug_key}' missing required field: '{f}'")

    def test_pharmacokinetic_parameter_ranges(self):
        for drug_key, details in self.drugs.items():
            f = details["bioavailability_f"]
            self.assertGreaterEqual(f, 0.0, f"{drug_key}: bioavailability F must be >= 0.0")
            self.assertLessEqual(f, 1.0, f"{drug_key}: bioavailability F must be <= 1.0")

            ke = details["ke"]
            self.assertGreater(ke, 0.0, f"{drug_key}: elimination rate ke must be > 0.0")

            t_half = details["half_life_hours"]
            self.assertGreater(t_half, 0.0, f"{drug_key}: half-life must be > 0.0")

            vd = details["vd_liters_per_kg"]
            self.assertGreater(vd, 0.0, f"{drug_key}: Vd must be > 0.0")

    def test_brand_name_resolution(self):
        # Cardiology
        self.assertEqual(self.db.get_canonical_name("Plavix"), "clopidogrel")
        self.assertEqual(self.db.get_canonical_name("Coumadin"), "warfarin")
        self.assertEqual(self.db.get_canonical_name("Toprol-XL"), "metoprolol")
        self.assertEqual(self.db.get_canonical_name("Lipitor"), "atorvastatin")
        # Psychiatry
        self.assertEqual(self.db.get_canonical_name("Prozac"), "fluoxetine")
        self.assertEqual(self.db.get_canonical_name("Lexapro"), "escitalopram")
        self.assertEqual(self.db.get_canonical_name("Tegretol"), "carbamazepine")
        # Infectious disease
        self.assertEqual(self.db.get_canonical_name("Ziagen"), "abacavir")
        self.assertEqual(self.db.get_canonical_name("Vfend"), "voriconazole")
        # Pain
        self.assertEqual(self.db.get_canonical_name("Ultram"), "tramadol")
        self.assertEqual(self.db.get_canonical_name("Celebrex"), "celecoxib")

    def test_therapeutic_areas_representation(self):
        areas = {d["therapeutic_area"] for d in self.drugs.values()}
        expected = {"Cardiology", "Psychiatry", "Oncology", "Infectious Disease", "Pain", "Endocrinology"}
        for exp in expected:
            self.assertIn(exp, areas, f"Therapeutic area '{exp}' should be represented in drug database")


class TestAlleleRegistry(unittest.TestCase):
    """Validates star-allele to metabolizer phenotype translation algorithms."""

    def test_cyp2c19_phenotypes(self):
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*1/*1"), MetabolizerPhenotype.NORMAL)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*1/*2"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*1/*3"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*2/*2"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*2/*3"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*1/*17"), MetabolizerPhenotype.RAPID)
        self.assertEqual(AlleleRegistry.get_cyp2c19_phenotype("*17/*17"), MetabolizerPhenotype.ULTRA_RAPID)

    def test_cyp2d6_phenotypes(self):
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*1/*1"), MetabolizerPhenotype.NORMAL)
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*1/*4"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*4/*4"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*3/*4"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*1xN/*1"), MetabolizerPhenotype.ULTRA_RAPID)
        self.assertEqual(AlleleRegistry.get_cyp2d6_phenotype("*1/*1x2"), MetabolizerPhenotype.ULTRA_RAPID)

    def test_cyp2c9_phenotypes(self):
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*1/*1"), MetabolizerPhenotype.NORMAL)
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*1/*2"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*1/*3"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*2/*2"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*2/*3"), MetabolizerPhenotype.POOR)
        self.assertEqual(AlleleRegistry.get_cyp2c9_phenotype("*3/*3"), MetabolizerPhenotype.POOR)

    def test_dpyd_phenotypes(self):
        self.assertEqual(AlleleRegistry.get_dpyd_phenotype("*1/*1"), MetabolizerPhenotype.NORMAL)
        self.assertEqual(AlleleRegistry.get_dpyd_phenotype("*1/*2A"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_dpyd_phenotype("*2A/*2A"), MetabolizerPhenotype.POOR)

    def test_tpmt_phenotypes(self):
        self.assertEqual(AlleleRegistry.get_tpmt_phenotype("*1/*1"), MetabolizerPhenotype.NORMAL)
        self.assertEqual(AlleleRegistry.get_tpmt_phenotype("*1/*3A"), MetabolizerPhenotype.INTERMEDIATE)
        self.assertEqual(AlleleRegistry.get_tpmt_phenotype("*3A/*3A"), MetabolizerPhenotype.POOR)


class TestPharmacogenomicsClinicalScenarios(unittest.TestCase):
    """Validates CPIC / DPWG clinical safety scenarios and alert triggers."""

    @classmethod
    def setUpClass(cls):
        cls.engine = PharmacogenomicsEngine()

    def test_abacavir_hla_b5701_contraindication(self):
        genotype = {"HLA-B*5701": "Positive"}
        res = self.engine.assess_patient_risk(genotype, ["Abacavir"])

        self.assertIn("Abacavir", res["contraindicated_drugs"])
        self.assertEqual(res["overall_hazard_score"], 99)
        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.CONTRAINDICATED.value)
        self.assertEqual(alert["gene"], "HLA-B*5701")
        self.assertIn("hypersensitivity", alert["summary"].lower())

    def test_abacavir_hla_b5701_negative_is_safe(self):
        genotype = {"HLA-B*5701": "Negative"}
        res = self.engine.assess_patient_risk(genotype, ["Abacavir"])
        self.assertEqual(len(res["alerts"]), 0)
        self.assertNotIn("Abacavir", res["contraindicated_drugs"])

    def test_carbamazepine_hla_b1502_contraindication(self):
        genotype = {"HLA-B*1502": "Positive"}
        res = self.engine.assess_patient_risk(genotype, ["Tegretol"])  # brand lookup

        self.assertIn("Carbamazepine", res["contraindicated_drugs"])
        self.assertEqual(res["overall_hazard_score"], 99)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.CONTRAINDICATED.value)
        self.assertIn("Stevens-Johnson", alert["summary"])

    def test_clopidogrel_cyp2c19_poor_metabolizer(self):
        genotype = {"CYP2C19": "*2/*2"}
        res = self.engine.assess_patient_risk(genotype, ["Plavix"])

        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.HIGH_RISK.value)
        self.assertEqual(alert["gene"], "CYP2C19")
        self.assertIn("stent thrombosis", alert["summary"].lower())
        self.assertIn("Prasugrel", alert["recommendation"])

    def test_codeine_cyp2d6_ultrarapid_metabolizer_toxicity(self):
        genotype = {"CYP2D6": "*1xN/*1"}
        res = self.engine.assess_patient_risk(genotype, ["Codeine"])

        self.assertIn("Codeine", res["contraindicated_drugs"])
        self.assertEqual(res["overall_hazard_score"], 99)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.CONTRAINDICATED.value)
        self.assertIn("respiratory depression", alert["summary"].lower())

    def test_codeine_cyp2d6_poor_metabolizer_failure(self):
        genotype = {"CYP2D6": "*4/*4"}
        res = self.engine.assess_patient_risk(genotype, ["Codeine"])

        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.HIGH_RISK.value)
        self.assertIn("analgesia", alert["summary"].lower())

    def test_tamoxifen_cyp2d6_poor_metabolizer_cancer_recurrence(self):
        genotype = {"CYP2D6": "*4/*4"}
        res = self.engine.assess_patient_risk(genotype, ["Tamoxifen"])

        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.HIGH_RISK.value)
        self.assertIn("recurrence", alert["summary"].lower())
        self.assertIn("aromatase inhibitor", alert["recommendation"].lower())

    def test_warfarin_cyp2c9_and_vkorc1_sensitivity(self):
        # Sensitive combo: CYP2C9 *3/*3 and VKORC1 -1639 A/A
        genotype = {
            "CYP2C9": "*3/*3",
            "VKORC1": "-1639 A/A"
        }
        res = self.engine.assess_patient_risk(genotype, ["Warfarin"])

        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["severity"], PGxSeverity.HIGH_RISK.value)
        self.assertIn("bleeding", alert["clinical_implication"].lower() or alert["summary"].lower())

        # Test internal warfarin calculator directly
        calc = self.engine.calculate_warfarin_sensitivity("*3/*3", "A/A")
        self.assertGreaterEqual(calc["estimated_dose_reduction_percent"], 50)
        self.assertLessEqual(calc["recommended_starting_dose_mg"], 2.0)

    def test_dpyd_fluorouracil_poor_metabolizer_contraindication(self):
        genotype = {"DPYD": "*2A/*2A"}
        res = self.engine.assess_patient_risk(genotype, ["5-FU", "Fluorouracil"])
        self.assertIn("Fluorouracil", res["contraindicated_drugs"])
        self.assertEqual(res["overall_hazard_score"], 99)


class TestPhenoconversionEngine(unittest.TestCase):
    """Validates drug-drug-gene phenocopy conversion mechanics."""

    @classmethod
    def setUpClass(cls):
        cls.engine = PharmacogenomicsEngine()

    def test_fluoxetine_phenoconverts_cyp2d6_nm_to_pm(self):
        # Patient is genetically CYP2D6 *1/*1 (Normal Metabolizer)
        genotype = {"CYP2D6": "*1/*1"}
        # But is taking Fluoxetine (potent CYP2D6 inhibitor) + Tamoxifen
        medications = ["Fluoxetine", "Tamoxifen"]
        res = self.engine.assess_patient_risk(genotype, medications)

        self.assertIn("CYP2D6", res["effective_phenotypes"])
        self.assertEqual(res["effective_phenotypes"]["CYP2D6"], MetabolizerPhenotype.POOR.value)
        self.assertGreater(len(res["phenoconversion_events"]), 0)

        # Tamoxifen should receive high-risk alert due to phenoconversion
        tamoxifen_alerts = [a for a in res["alerts"] if a["drug"] == "Tamoxifen"]
        self.assertEqual(len(tamoxifen_alerts), 1)
        self.assertTrue(tamoxifen_alerts[0]["phenoconverted"])
        self.assertEqual(tamoxifen_alerts[0]["severity"], PGxSeverity.HIGH_RISK.value)

    def test_omeprazole_phenoconverts_cyp2c19_nm_affecting_clopidogrel(self):
        # Patient is genetically CYP2C19 *1/*1 (Normal Metabolizer)
        genotype = {"CYP2C19": "*1/*1"}
        # Patient takes Omeprazole + Clopidogrel
        medications = ["Omeprazole", "Clopidogrel"]
        res = self.engine.assess_patient_risk(genotype, medications)

        self.assertEqual(
            res["effective_phenotypes"]["CYP2C19"],
            MetabolizerPhenotype.INTERMEDIATE.value
        )
        self.assertGreater(len(res["phenoconversion_events"]), 0)

        clop_alerts = [a for a in res["alerts"] if a["drug"] == "Clopidogrel"]
        self.assertEqual(len(clop_alerts), 1)
        self.assertTrue(clop_alerts[0]["phenoconverted"])


class TestPharmacogenomicsAPI(unittest.TestCase):
    """End-to-end integration tests for FastAPI PGx endpoints."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from main import app
        cls.client = TestClient(app)

    def test_get_drugs_endpoint(self):
        resp = self.client.get("/api/drugs")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total_count"], 50)
        self.assertIn("warfarin", data["drugs"])

    def test_get_specific_drug(self):
        resp = self.client.get("/api/drugs/warfarin")
        self.assertEqual(resp.status_code, 200)
        drug = resp.json()
        self.assertEqual(drug["generic_name"], "Warfarin")
        self.assertEqual(drug["bioavailability_f"], 1.0)
        self.assertIn("CYP2C9", drug["high_risk_pgx_genes"])

    def test_post_pgx_audit_endpoint(self):
        payload = {
            "patient_id": "TEST_PT_01",
            "medications": ["Abacavir", "Aspirin"],
            "patient_genotype": {
                "HLA-B*5701": "Positive"
            }
        }
        resp = self.client.post("/api/pgx/audit", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "CRITICAL_ACTION_REQUIRED")
        self.assertIn("Abacavir", data["contraindicated_drugs"])
        self.assertEqual(data["overall_hazard_score"], 99)

    def test_post_audit_regimen_with_genotype(self):
        payload = {
            "patient_id": "TEST_PT_02",
            "medications": [
                {"name": "Clopidogrel", "dose": "75mg"},
                {"name": "Omeprazole", "dose": "20mg"}
            ],
            "patient_genotype": {
                "CYP2C19": "*2/*2"
            }
        }
        resp = self.client.post("/api/audit-regimen", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pharmacogenomics", data)
        self.assertIsNotNone(data["pharmacogenomics"])
        self.assertGreaterEqual(data["hazard_score"], 88)


if __name__ == "__main__":
    unittest.main()
