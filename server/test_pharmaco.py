"""
Pharmaco-Llama Full Backend & PK Math Unit Test Suite
"""

import unittest
from pk_math import (
    one_compartment_oral_absorption,
    calculate_cyp_inhibition,
    calculate_half_life,
    simulate_warfarin_omeprazole_crisis
)
from openfda_engine import query_drug_label

class TestPharmacoLlama(unittest.TestCase):
    
    def test_pk_oral_absorption_curve(self):
        times = [0, 4, 8, 12, 24]
        # Standard oral dosing curve
        curve = one_compartment_oral_absorption(
            dose_mg=5.0, bioavailability_f=1.0, ka=1.2, ke=0.0173, vd_liters=10.0, time_hours=times
        )
        self.assertEqual(len(curve), 5)
        self.assertEqual(curve[0], 0.0)
        self.assertGreater(curve[1], curve[0])  # Absorption phase
        self.assertGreater(curve[1], curve[4])  # Elimination phase

    def test_cyp_inhibition_math(self):
        ke_base = 0.02
        inhibitor_conc = 10.0
        ki = 10.0
        # Factor = 1 + (10/10) = 2.0 -> ke should be halved to 0.01
        ke_inh, fold = calculate_cyp_inhibition(ke_base, inhibitor_conc, ki)
        self.assertEqual(fold, 2.0)
        self.assertEqual(ke_inh, 0.01)

    def test_half_life_calculation(self):
        ke = 0.0173  # Warfarin standard ke
        t_half = calculate_half_life(ke)
        self.assertAlmostEqual(t_half, 40.1, delta=0.5)

    def test_warfarin_simulation(self):
        sim = simulate_warfarin_omeprazole_crisis()
        self.assertEqual(sim["drug"], "Warfarin Sodium")
        self.assertGreater(sim["inhibited_t_half_h"], sim["baseline_t_half_h"])
        self.assertEqual(sim["bleeding_relative_risk"], 4.2)

    def test_openfda_query(self):
        res = query_drug_label("warfarin")
        self.assertIn("status", res)
        self.assertIn("boxed_warning", res)
        self.assertTrue(len(res["boxed_warning"]) > 0)

if __name__ == '__main__':
    unittest.main()
