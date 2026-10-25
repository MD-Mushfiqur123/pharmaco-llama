"""
Pharmaco-Llama: CPIC (Clinical Pharmacogenetics Implementation Consortium) Guideline Engine
Implements Official Clinical Level A & B Pharmacogenomic Dosing Rules & Diplotype Translation
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

from typing import Dict, List, Any, Optional

# Official CPIC Level A Gene-Drug Clinical Guideline Rules
CPIC_GUIDELINES: Dict[str, Dict[str, Any]] = {
    "CYP2C19": {
        "Clopidogrel": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Significantly reduced active thiol metabolite generation; diminished platelet inhibition; increased risk of stent thrombosis and major adverse cardiovascular events (MACE).",
                "recommendation": "Avoid Clopidogrel. Prescribe alternative antiplatelet agent: Prasugrel (if no history of stroke/TIA) or Ticagrelor at standard doses.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            },
            "Intermediate Metabolizer": {
                "activity_score": 0.5,
                "clinical_impact": "Moderately reduced active metabolite; suboptimal antiplatelet response.",
                "recommendation": "Consider alternative antiplatelet (Prasugrel or Ticagrelor) especially in acute coronary syndrome (ACS) or PCI settings.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            },
            "Ultrarapid Metabolizer": {
                "activity_score": 2.5,
                "clinical_impact": "Normal to slightly enhanced active metabolite; nominal or elevated bleeding risk.",
                "recommendation": "Prescribe standard dose (75 mg/day). Monitor for minor bleeding episodes.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        },
        "Voriconazole": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Markedly elevated voriconazole plasma concentrations; increased risk of visual hallucinations, hepatotoxicity, and QTc prolongation.",
                "recommendation": "Select alternative antifungal agent not dependent on CYP2C19 (e.g., Isavuconazole, Posaconazole, Liposomal Amphotericin B) or reduce dose by 50% with strict Therapeutic Drug Monitoring (TDM).",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            },
            "Ultrarapid Metabolizer": {
                "activity_score": 2.5,
                "clinical_impact": "Subtherapeutic plasma concentrations (<1.0 mg/L); high risk of invasive fungal infection treatment failure.",
                "recommendation": "Select alternative antifungal (Liposomal Amphotericin B or Posaconazole) or increase dose with intensive TDM.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        },
        "Escitalopram": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "2-fold increased plasma exposure; risk of concentration-dependent QTc prolongation.",
                "recommendation": "Initiate at 50% standard dose (max 10 mg/day) or switch to non-CYP2C19 antidepressant.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        }
    },
    "CYP2D6": {
        "Codeine": {
            "Ultrarapid Metabolizer": {
                "activity_score": 3.0,
                "clinical_impact": "Extremely rapid conversion to morphine; life-threatening or fatal respiratory depression, especially in pediatric post-tonsillectomy or breastfed infants.",
                "recommendation": "CONTRAINDICATED. Avoid codeine entirely. Prescribe non-opioid analgesic (Acetaminophen, NSAID) or direct-acting opioid unaffected by CYP2D6 (Morphine, Hydromorphone).",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            },
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Inability to bioactivate codeine into morphine; total analgesia failure.",
                "recommendation": "Avoid codeine. Prescribe direct opioid (Morphine, Oxycodone) or non-opioid multimodal analgesia.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        },
        "Tamoxifen": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Subtherapeutic formation of endoxifen (active metabolite); significantly worse relapse-free breast cancer survival.",
                "recommendation": "Switch to aromatase inhibitor (Anastrozole, Letrozole) if postmenopausal, or consider increasing tamoxifen dose to 40 mg/day under oncologic supervision.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        },
        "Ondansetron": {
            "Ultrarapid Metabolizer": {
                "activity_score": 3.0,
                "clinical_impact": "Ultra-fast clearance; antiemetic prophylaxis failure during chemotherapy or postoperative recovery.",
                "recommendation": "Select alternative antiemetic not primarily cleared by CYP2D6 (e.g., Granisetron, Palonosetron, Aprepitant).",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        }
    },
    "SLCO1B1": {
        "Simvastatin": {
            "Poor Function": {
                "activity_score": 0.0,
                "clinical_impact": "Impaired OATP1B1 hepatic uptake transporter; 221% increase in simvastatin acid AUC; high risk of severe myopathy and rhabdomyolysis.",
                "recommendation": "Avoid simvastatin doses >20 mg/day or switch to pravastatin or rosuvastatin at lower starting doses.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            },
            "Decreased Function": {
                "activity_score": 0.5,
                "clinical_impact": "Moderately elevated simvastatin systemic exposure; elevated myopathy risk.",
                "recommendation": "Do not exceed simvastatin 20-40 mg/day; monitor for unexplained muscle pain or weakness.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": False
            }
        }
    },
    "DPYD": {
        "Fluorouracil": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Complete deficiency of dihydropyrimidine dehydrogenase (DPD); fatal drug accumulation, severe mucositis, neutropenic sepsis, and death.",
                "recommendation": "CONTRAINDICATED. Do not administer Fluorouracil (5-FU) or Capecitabine. Select alternative non-fluoropyrimidine oncologic regimen.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            },
            "Intermediate Metabolizer": {
                "activity_score": 1.0,
                "clinical_impact": "Partial DPD enzyme deficiency; high risk of grade 3-4 toxicities.",
                "recommendation": "Reduce starting dose by 50%; titrate dose based on toxicity and therapeutic drug monitoring.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            }
        }
    },
    "TPMT": {
        "Azathioprine": {
            "Poor Metabolizer": {
                "activity_score": 0.0,
                "clinical_impact": "Shunting of thiopurine metabolism towards thioguanine nucleotides (TGN); life-threatening pancytopenia and severe bone marrow failure.",
                "recommendation": "For malignant conditions: reduce dose by 90% (administer 10% of standard dose) thrice weekly. For non-malignant: select alternative immunosuppressant.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            }
        }
    },
    "HLA-B": {
        "Abacavir": {
            "*57:01 Positive": {
                "activity_score": None,
                "clinical_impact": "Immunologically-mediated fatal hypersensitivity syndrome: multisystem organ failure, severe fever, rash, dyspnea, and anaphylactoid shock.",
                "recommendation": "ABSOLUTELY CONTRAINDICATED. Never initiate Abacavir. Never rechallenge. Select alternative antiretroviral agent.",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            }
        },
        "Carbamazepine": {
            "*15:02 Positive": {
                "activity_score": None,
                "clinical_impact": "Severe cutaneous adverse reactions (SCAR): Stevens-Johnson syndrome (SJS) and Toxic Epidermal Necrolysis (TEN).",
                "recommendation": "CONTRAINDICATED. Avoid Carbamazepine and Oxcarbazepine. Select alternative anticonvulsant (Valproate, Levetiracetam).",
                "evidence_level": "CPIC Level A",
                "fda_boxed_warning": True
            }
        }
    }
}

class CPICGuidelineEngine:
    """
    Evaluates patient genotypes against official CPIC Level A clinical consensus guidelines.
    """
    def __init__(self):
        self.guidelines = CPIC_GUIDELINES

    def evaluate_pgx_guideline(
        self,
        gene: str,
        phenotype_or_allele: str,
        drug_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Queries CPIC clinical dosing rules for a specific gene, phenotype, and drug combination.
        """
        gene_upper = gene.strip().upper()
        drug_title = drug_name.strip().capitalize()
        
        gene_data = self.guidelines.get(gene_upper)
        if not gene_data:
            return None
            
        drug_rules = gene_data.get(drug_title)
        if not drug_rules:
            return None
            
        # Match phenotype or allele
        for key, rule in drug_rules.items():
            if key.lower() in phenotype_or_allele.lower() or phenotype_or_allele.lower() in key.lower():
                return {
                    "gene": gene_upper,
                    "drug": drug_title,
                    "phenotype": key,
                    "guideline": rule
                }
                
        return None

    def scan_regimen_cpic(
        self,
        patient_genotypes: Dict[str, str],
        active_drugs: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Scans a complete multi-drug regimen against the patient's full genetic profile.
        """
        alerts = []
        for drug in active_drugs:
            for gene, phenotype in patient_genotypes.items():
                result = self.evaluate_pgx_guideline(gene, phenotype, drug)
                if result:
                    alerts.append(result)
        return alerts
