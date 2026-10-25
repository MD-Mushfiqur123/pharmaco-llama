"""
Pharmaco-Llama: Monte Carlo Population Pharmacokinetics (PopPK) Simulator
Virtual Clinical Trial Cohort Simulator with Inter-Individual Variability (IIV) & Target Attainment
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

import numpy as np
from typing import Dict, List, Any, Optional

class PopulationPKSimulator:
    """
    Simulates virtual clinical trial cohorts using Non-Linear Mixed Effects (NLME) modeling principles.
    CL_i = theta_CL * (WT_i/70)^0.75 * (CrCl_i/100)^0.5 * exp(eta_CL)
    V_i  = theta_V  * (WT_i/70)^1.0  * exp(eta_V)
    """
    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)

    def generate_virtual_cohort(
        self,
        cohort_size: int = 500,
        mean_age: float = 65.0,
        std_age: float = 12.0,
        mean_weight: float = 72.0,
        std_weight: float = 14.0,
        mean_gfr: float = 65.0,
        std_gfr: float = 20.0,
        pct_male: float = 0.55
    ) -> Dict[str, np.ndarray]:
        """
        Generates realistic correlated demographic profiles for virtual patients.
        """
        ages = np.clip(self.rng.normal(mean_age, std_age, cohort_size), 18.0, 95.0)
        weights = np.clip(self.rng.normal(mean_weight, std_weight, cohort_size), 40.0, 140.0)
        gfrs = np.clip(self.rng.normal(mean_gfr, std_gfr, cohort_size), 10.0, 130.0)
        sexes = self.rng.binomial(1, pct_male, cohort_size)  # 1 = male, 0 = female
        
        return {
            "age": ages,
            "weight": weights,
            "gfr": gfrs,
            "is_male": sexes
        }

    def simulate_cohort_trials(
        self,
        dose_mg: float = 100.0,
        theta_ka: float = 1.2,
        theta_cl: float = 4.5,
        theta_vd: float = 35.0,
        omega_cl: float = 0.35,  # 35% inter-individual coefficient of variation in clearance
        omega_vd: float = 0.25,  # 25% CV in volume of distribution
        therapeutic_min_mg_l: float = 0.8,
        therapeutic_max_mg_l: float = 3.5,
        cohort_size: int = 500,
        time_span_h: float = 48.0,
        time_points: int = 25
    ) -> Dict[str, Any]:
        """
        Runs full population simulation and computes percentiles & therapeutic target attainment.
        """
        cohort = self.generate_virtual_cohort(cohort_size=cohort_size)
        times = np.linspace(0.0, time_span_h, time_points)
        
        # Inter-Individual Variability (IIV)
        eta_cl = self.rng.normal(0.0, omega_cl, cohort_size)
        eta_vd = self.rng.normal(0.0, omega_vd, cohort_size)
        
        # Individual clearances and volumes
        # Allometric weight scaling: exponent 0.75 for clearance, 1.0 for volume
        ind_cl = theta_cl * ((cohort["weight"] / 70.0) ** 0.75) * ((cohort["gfr"] / 90.0) ** 0.5) * np.exp(eta_cl)
        ind_vd = theta_vd * (cohort["weight"] / 70.0) * np.exp(eta_vd)
        ind_ke = ind_cl / ind_vd
        
        # Concentration matrix: shape (cohort_size, time_points)
        conc_matrix = np.zeros((cohort_size, time_points))
        
        for i in range(cohort_size):
            ka = theta_ka
            ke = ind_ke[i]
            vd = ind_vd[i]
            if abs(ka - ke) < 1e-4:
                ke += 1e-4
            factor = (dose_mg * ka) / (vd * (ka - ke))
            c_t = factor * (np.exp(-ke * times) - np.exp(-ka * times))
            conc_matrix[i, :] = np.maximum(0.0, c_t)
            
        # Statistical Percentiles across virtual cohort
        p5 = np.percentile(conc_matrix, 5, axis=0)
        p25 = np.percentile(conc_matrix, 25, axis=0)
        p50 = np.percentile(conc_matrix, 50, axis=0)  # Median
        p75 = np.percentile(conc_matrix, 75, axis=0)
        p95 = np.percentile(conc_matrix, 95, axis=0)
        
        # Target Attainment Evaluation (at steady state or peak 2-8 hours)
        peak_concs = np.max(conc_matrix, axis=1)
        subtherapeutic_count = int(np.sum(peak_concs < therapeutic_min_mg_l))
        toxic_count = int(np.sum(peak_concs > therapeutic_max_mg_l))
        therapeutic_count = cohort_size - subtherapeutic_count - toxic_count
        
        therapeutic_target_attainment_pct = round((therapeutic_count / cohort_size) * 100.0, 1)
        toxic_exposure_risk_pct = round((toxic_count / cohort_size) * 100.0, 1)
        subtherapeutic_failure_risk_pct = round((subtherapeutic_count / cohort_size) * 100.0, 1)
        
        return {
            "cohort_size": cohort_size,
            "time_points_hours": [round(t, 2) for t in times.tolist()],
            "percentiles": {
                "p5_mg_l": [round(val, 4) for val in p5.tolist()],
                "p25_mg_l": [round(val, 4) for val in p25.tolist()],
                "p50_median_mg_l": [round(val, 4) for val in p50.tolist()],
                "p75_mg_l": [round(val, 4) for val in p75.tolist()],
                "p95_mg_l": [round(val, 4) for val in p95.tolist()]
            },
            "target_attainment": {
                "target_therapeutic_window_mg_l": [therapeutic_min_mg_l, therapeutic_max_mg_l],
                "therapeutic_attainment_pct": therapeutic_target_attainment_pct,
                "toxic_exposure_risk_pct": toxic_exposure_risk_pct,
                "subtherapeutic_failure_risk_pct": subtherapeutic_failure_risk_pct
            },
            "demographic_summary": {
                "mean_age": round(float(np.mean(cohort["age"])), 1),
                "mean_weight_kg": round(float(np.mean(cohort["weight"])), 1),
                "mean_gfr_ml_min": round(float(np.mean(cohort["gfr"])), 1)
            }
        }
