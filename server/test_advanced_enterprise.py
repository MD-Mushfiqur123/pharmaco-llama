"""
Enterprise Clinical Suite Unit Tests:
- CPIC Guideline Level A Rules
- Monte Carlo Population PK Simulation (500 virtual patients)
- DDGI Phenoconversion Calculator
- AGS Beers Criteria & Anticholinergic Burden (ACB) Scale
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
    from server.cpic_engine import CPICGuidelineEngine
    from server.population_pk import PopulationPKSimulator
    from server.ddgi_phenoconversion import PhenoconversionEngine
    from server.clinical_decision_support import ClinicalDecisionSupportEngine
except ImportError:
    from cpic_engine import CPICGuidelineEngine
    from population_pk import PopulationPKSimulator
    from ddgi_phenoconversion import PhenoconversionEngine
    from clinical_decision_support import ClinicalDecisionSupportEngine

class TestAdvancedEnterpriseSuite(unittest.TestCase):

    def setUp(self):
        self.cpic = CPICGuidelineEngine()
        self.poppk = PopulationPKSimulator(random_seed=123)
        self.pheno = PhenoconversionEngine()
        self.cdss = ClinicalDecisionSupportEngine()

    # 1. CPIC Guideline Tests
    def test_cpic_clopidogrel_poor_metabolizer(self):
        alert = self.cpic.evaluate_pgx_guideline("CYP2C19", "Poor Metabolizer", "Clopidogrel")
        self.assertIsNotNone(alert)
        self.assertIn("Prasugrel", alert["guideline"]["recommendation"])
        self.assertTrue(alert["guideline"]["fda_boxed_warning"])

    def test_cpic_codeine_ultrarapid_fatal_alert(self):
        alert = self.cpic.evaluate_pgx_guideline("CYP2D6", "Ultrarapid Metabolizer", "Codeine")
        self.assertIsNotNone(alert)
        self.assertIn("CONTRAINDICATED", alert["guideline"]["recommendation"])

    def test_cpic_regimen_scanning(self):
        genotypes = {"CYP2C19": "Poor Metabolizer", "SLCO1B1": "Poor Function"}
        drugs = ["Clopidogrel", "Simvastatin", "Metformin"]
        alerts = self.cpic.scan_regimen_cpic(genotypes, drugs)
        self.assertEqual(len(alerts), 2)

    # 2. Monte Carlo PopPK Tests
    def test_population_pk_simulation(self):
        sim = self.poppk.simulate_cohort_trials(
            dose_mg=50.0,
            theta_ka=1.0,
            theta_cl=5.0,
            theta_vd=40.0,
            cohort_size=300,
            time_span_h=24.0
        )
        self.assertEqual(sim["cohort_size"], 300)
        self.assertEqual(len(sim["time_points_hours"]), 25)
        self.assertIn("percentiles", sim)
        self.assertEqual(len(sim["percentiles"]["p50_median_mg_l"]), 25)
        self.assertGreater(sim["target_attainment"]["therapeutic_attainment_pct"], 0.0)

    # 3. Phenoconversion Tests
    def test_cyp2d6_phenoconversion_by_fluoxetine(self):
        res = self.pheno.calculate_effective_phenotype(
            gene="CYP2D6",
            baseline_phenotype="Normal Metabolizer",
            co_medications=["Fluoxetine", "Codeine"]
        )
        self.assertTrue(res["is_phenoconverted"])
        self.assertEqual(res["effective_phenotype"], "Phenoconverted Poor Metabolizer")
        self.assertIn("Fluoxetine", res["culprit_inhibitor_drugs"])

    # 4. Clinical Decision Support System Tests
    def test_anticholinergic_burden_high(self):
        drugs = ["Amitriptyline", "Diphenhydramine", "Warfarin"]
        acb = self.cdss.calculate_anticholinergic_burden(drugs)
        self.assertGreaterEqual(acb["total_acb_score"], 6)
        self.assertEqual(acb["risk_level"], "HIGH_COGNITIVE_RISK")

    def test_beers_criteria_elderly_pims(self):
        pims = self.cdss.evaluate_geriatric_beers(age=75, medications=["Diazepam", "Diphenhydramine"])
        self.assertEqual(len(pims), 2)
        criteria = [p["criteria"] for p in pims]
        self.assertTrue(all("Beers" in c for c in criteria))

    def test_renal_kdigo_contraindications(self):
        alerts = self.cdss.evaluate_renal_appropriateness(egfr=25.0, medications=["Metformin", "Spironolactone", "Ibuprofen"])
        self.assertEqual(len(alerts), 3)
        self.assertTrue(all(a["level"] == "CONTRAINDICATED" for a in alerts))

if __name__ == "__main__":
    unittest.main()
