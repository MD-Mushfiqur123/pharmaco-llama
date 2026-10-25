"""
Pharmaco-Llama: Physiologically-Based Pharmacokinetic (PBPK) ODE Simulation Engine
Inspired by PK-Sim (Open Systems Pharmacology Suite)
Mathematical Modeling of Multi-Compartment Virtual Patient Drug Distribution & Clearance
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict, List, Any, Optional

class PBPKVirtualPatient:
    """
    Physiological parameter set for a virtual patient scaled by demographics.
    """
    def __init__(
        self,
        age: float = 65.0,
        weight_kg: float = 70.0,
        height_cm: float = 170.0,
        sex: str = "male",
        egfr_ml_min: float = 60.0,
        serum_albumin_g_dl: float = 4.0
    ):
        self.age = age
        self.weight_kg = weight_kg
        self.height_cm = height_cm
        self.sex = sex.lower()
        self.egfr = egfr_ml_min
        self.albumin = serum_albumin_g_dl
        
        # Calculate Body Surface Area (DuBois & DuBois)
        self.bsa = 0.007184 * (self.weight_kg ** 0.425) * (self.height_cm ** 0.725)
        
        # Organ physiological volumes (Liters) based on PK-Sim standard population scaling
        # Central blood/plasma volume
        base_plasma = 3.0 if self.sex == "male" else 2.6
        self.v_central = base_plasma * (self.weight_kg / 70.0)
        
        # Liver volume (~2% of body weight, reduced with age > 60)
        age_liver_factor = max(0.65, 1.0 - max(0.0, (self.age - 50) * 0.006))
        self.v_liver = (0.022 * self.weight_kg) * age_liver_factor
        
        # Kidney volume (~0.4% of body weight)
        self.v_kidney = 0.0045 * self.weight_kg
        
        # Peripheral tissue volume (muscle, adipose, interstitial fluid)
        self.v_peripheral = max(10.0, (self.weight_kg * 0.35))
        
        # Blood flow rates (L/h)
        cardiac_output_l_h = 300.0 * (self.bsa / 1.73)
        self.q_hepatic = cardiac_output_l_h * 0.25  # ~25% to liver
        self.q_renal = cardiac_output_l_h * (min(120.0, max(15.0, self.egfr)) / 120.0) * 0.20  # scaled by GFR
        self.q_intercompartmental = 8.5 * (self.weight_kg / 70.0)  # Plasma <-> Peripheral exchange

def pbpk_ode_system(t: float, y: List[float], params: Dict[str, float]) -> List[float]:
    """
    System of Ordinary Differential Equations (ODEs) for 4-compartment PBPK:
    y[0] = A_gut (mass in GI tract)
    y[1] = A_central (mass in systemic plasma)
    y[2] = A_liver (mass in hepatic compartment)
    y[3] = A_peripheral (mass in deep peripheral tissues)
    """
    A_gut, A_central, A_liver, A_peripheral = y
    
    ka = params["ka"]
    vc = params["vc"]
    vl = params["vl"]
    vp = params["vp"]
    q_l = params["q_l"]
    q_p = params["q_p"]
    cl_hep = params["cl_hep"]
    cl_ren = params["cl_ren"]
    kp_liver = params.get("kp_liver", 1.2)
    kp_periph = params.get("kp_periph", 0.9)
    
    # Concentrations in each compartment
    c_central = max(0.0, A_central / vc)
    c_liver_tissue = max(0.0, A_liver / vl)
    c_liver_blood = c_liver_tissue / kp_liver
    c_periph_tissue = max(0.0, A_peripheral / vp)
    c_periph_blood = c_periph_tissue / kp_periph
    
    # 1. GI Tract Absorption
    dA_gut_dt = -ka * A_gut
    
    # 2. Hepatic Compartment
    # Inflow from hepatic artery/portal, outflow, minus intrinsic metabolic clearance
    dA_liver_dt = (q_l * c_central) - (q_l * c_liver_blood) - (cl_hep * c_liver_tissue)
    
    # 3. Peripheral Compartment
    # Intercompartmental transfer (bidirectional diffusion)
    dA_peripheral_dt = q_p * (c_central - c_periph_blood)
    
    # 4. Central Systemic Plasma Compartment
    # Input from GI absorption (first-pass) + return from liver - liver entry - peripheral flow - renal clearance
    dA_central_dt = (ka * A_gut) + (q_l * c_liver_blood) - (q_l * c_central) - dA_peripheral_dt - (cl_ren * c_central)
    
    return [dA_gut_dt, dA_central_dt, dA_liver_dt, dA_peripheral_dt]

def simulate_pbpk(
    dose_mg: float,
    ka: float,
    ke: float,
    vd_base: float,
    f_bioavailability: float,
    patient: Optional[PBPKVirtualPatient] = None,
    cyp_inhibition_factor: float = 1.0,
    time_span_hours: float = 48.0,
    num_points: int = 100
) -> Dict[str, Any]:
    """
    Executes high-precision PBPK ODE simulation using SciPy solve_ivp (RK45).
    """
    if patient is None:
        patient = PBPKVirtualPatient()
        
    # Scale clearances
    total_cl = ke * vd_base * (patient.weight_kg / 70.0)
    # Apportion ~70% hepatic, ~30% renal base, scaled by clinical factors
    renal_fraction = min(0.8, max(0.1, (patient.egfr / 100.0) * 0.35))
    cl_ren = total_cl * renal_fraction * (patient.egfr / 90.0)
    cl_hep = (total_cl * (1.0 - renal_fraction)) * cyp_inhibition_factor
    
    # Tissue partition coefficients (PK-Sim Rodgers-Rowland approximation)
    kp_liver = 1.4
    kp_periph = max(0.5, min(3.5, vd_base / 2.0))
    
    params = {
        "ka": ka,
        "vc": patient.v_central,
        "vl": patient.v_liver,
        "vp": patient.v_peripheral,
        "q_l": patient.q_hepatic,
        "q_p": patient.q_intercompartmental,
        "cl_hep": cl_hep,
        "cl_ren": cl_ren,
        "kp_liver": kp_liver,
        "kp_periph": kp_periph
    }
    
    # Initial conditions: dose enters gut
    initial_gut = dose_mg * f_bioavailability
    y0 = [initial_gut, 0.0, 0.0, 0.0]
    
    t_eval = np.linspace(0.0, time_span_hours, num_points)
    
    sol = solve_ivp(
        fun=lambda t, y: pbpk_ode_system(t, y, params),
        t_span=(0.0, time_span_hours),
        y0=y0,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-5,
        atol=1e-7
    )
    
    if not sol.success:
        raise RuntimeError(f"PBPK ODE integration failed: {sol.message}")
        
    times = sol.t.tolist()
    c_central = [max(0.0, val / patient.v_central) for val in sol.y[1]]
    c_liver = [max(0.0, val / patient.v_liver) for val in sol.y[2]]
    c_peripheral = [max(0.0, val / patient.v_peripheral) for val in sol.y[3]]
    
    c_max = float(np.max(c_central))
    t_max = float(times[int(np.argmax(c_central))])
    # Trapezoidal AUC
    try:
        auc_0_t = float(np.trapezoid(c_central, times))
    except AttributeError:
        auc_0_t = float(np.trapz(c_central, times))
    
    return {
        "time_hours": [round(t, 2) for t in times],
        "c_plasma_mg_l": [round(c, 4) for c in c_central],
        "c_liver_tissue_mg_l": [round(c, 4) for c in c_liver],
        "c_peripheral_mg_l": [round(c, 4) for c in c_peripheral],
        "metrics": {
            "c_max_mg_l": round(c_max, 4),
            "t_max_hours": round(t_max, 2),
            "auc_0_last": round(auc_0_t, 2),
            "patient_egfr": patient.egfr,
            "patient_v_central_liters": round(patient.v_central, 2),
            "hepatic_clearance_l_h": round(cl_hep, 3),
            "renal_clearance_l_h": round(cl_ren, 3)
        }
    }
