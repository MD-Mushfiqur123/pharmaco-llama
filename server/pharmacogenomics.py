"""
Pharmaco-Llama High-Risk Pharmacogenomic (PGx) Risk & Clinical Decision Engine
Compliant with CPIC (Clinical Pharmacogenetics Implementation Consortium) & DPWG Guidelines
Author: Lead Pharmacogenomics & Clinical Database Engineer
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class PGxSeverity(str, Enum):
    CONTRAINDICATED = "CONTRAINDICATED"
    HIGH_RISK = "HIGH_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    INFORMATIONAL = "INFORMATIONAL"
    NORMAL = "NORMAL"


class MetabolizerPhenotype(str, Enum):
    ULTRA_RAPID = "Ultra-Rapid Metabolizer (UM)"
    RAPID = "Rapid Metabolizer (RM)"
    NORMAL = "Normal Metabolizer (NM)"
    INTERMEDIATE = "Intermediate Metabolizer (IM)"
    POOR = "Poor Metabolizer (PM)"
    INDETERMINATE = "Indeterminate"


@dataclass
class PGxAlert:
    drug: str
    gene: str
    severity: PGxSeverity
    phenotype: str
    alert_type: str
    summary: str
    clinical_implication: str
    recommendation: str
    guideline_source: str
    phenoconverted: bool = False
    perpetrator_drug: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class PhenoconversionEvent:
    gene: str
    perpetrator_drug: str
    baseline_phenotype: str
    effective_phenotype: str
    mechanism: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DrugDatabase:
    """Manages loading, searching, and caching of clinical drug parameters."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "drug_database.json")
        self.db_path = db_path
        self.drugs: Dict[str, Dict[str, Any]] = {}
        self.brand_to_generic: Dict[str, str] = {}
        self._load_database()

    def _load_database(self) -> None:
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Drug database not found at {self.db_path}")

        with open(self.db_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_drugs = data.get("drugs", {})
        for generic_key, details in raw_drugs.items():
            canonical_key = generic_key.lower().strip()
            self.drugs[canonical_key] = details

            # Register generic name
            self.brand_to_generic[canonical_key] = canonical_key
            self.brand_to_generic[details["generic_name"].lower().strip()] = canonical_key

            # Register brand names
            for brand in details.get("brand_names", []):
                self.brand_to_generic[brand.lower().strip()] = canonical_key

    def resolve_drug(self, drug_query: str) -> Optional[Dict[str, Any]]:
        clean_q = drug_query.lower().strip()
        # Direct key match
        if clean_q in self.drugs:
            return self.drugs[clean_q]

        # Brand / alias match
        if clean_q in self.brand_to_generic:
            return self.drugs[self.brand_to_generic[clean_q]]

        # Substring / fuzzy fallback
        for name, key in self.brand_to_generic.items():
            if name in clean_q or clean_q in name:
                return self.drugs[key]

        return None

    def get_canonical_name(self, drug_query: str) -> Optional[str]:
        drug = self.resolve_drug(drug_query)
        if drug:
            return drug["generic_name"].lower()
        return None

    def get_all_drugs(self) -> Dict[str, Dict[str, Any]]:
        return self.drugs


class AlleleRegistry:
    """Translates star-alleles and genotype diplotypes to clinical metabolizer phenotypes."""

    @staticmethod
    def normalize_diplotype(diplotype: str) -> str:
        clean = diplotype.strip().replace(" ", "")
        if "/" in clean:
            alleles = clean.split("/")
            return "/".join(sorted(alleles))
        return clean

    @classmethod
    def get_cyp2c19_phenotype(cls, diplotype: str) -> MetabolizerPhenotype:
        norm = cls.normalize_diplotype(diplotype)
        # Loss of function: *2, *3, *4, *5, *6, *7, *8
        # Gain of function: *17
        # Normal: *1
        if norm in ["*17/*17"]:
            return MetabolizerPhenotype.ULTRA_RAPID
        if norm in ["*1/*17"]:
            return MetabolizerPhenotype.RAPID
        if norm in ["*1/*1"]:
            return MetabolizerPhenotype.NORMAL
        if norm in ["*1/*2", "*1/*3", "*2/*17", "*3/*17"]:
            return MetabolizerPhenotype.INTERMEDIATE
        if norm in ["*2/*2", "*2/*3", "*3/*3"]:
            return MetabolizerPhenotype.POOR

        # Parsing generic patterns
        has_loss = "*2" in norm or "*3" in norm
        has_gain = "*17" in norm
        if "*2" in norm and "*3" in norm:
            return MetabolizerPhenotype.POOR
        if has_loss and not has_gain and "*1" not in norm:
            return MetabolizerPhenotype.POOR
        if has_loss:
            return MetabolizerPhenotype.INTERMEDIATE
        if has_gain:
            return MetabolizerPhenotype.RAPID
        return MetabolizerPhenotype.NORMAL

    @classmethod
    def get_cyp2d6_phenotype(cls, diplotype: str) -> MetabolizerPhenotype:
        norm = cls.normalize_diplotype(diplotype)

        # CPIC Activity Score table
        allele_activity = {
            "*1": 1.0,
            "*2": 1.0,
            "*33": 1.0,
            "*35": 1.0,
            "*9": 0.5,
            "*10": 0.25,
            "*17": 0.5,
            "*29": 0.5,
            "*41": 0.5,
            "*3": 0.0,
            "*4": 0.0,
            "*5": 0.0,
            "*6": 0.0,
            "*7": 0.0,
            "*8": 0.0,
            "*11": 0.0,
            "*15": 0.0,
            "*1xN": 2.0,
            "*1x2": 2.0,
            "*2xN": 2.0,
            "*2x2": 2.0,
        }

        # Check explicit dups/ultrarapid
        if "xN" in norm or "x2" in norm or "dup" in norm.lower():
            if "*4" not in norm and "*5" not in norm and "*3" not in norm:
                return MetabolizerPhenotype.ULTRA_RAPID

        parts = norm.split("/") if "/" in norm else [norm, "*1"]
        if len(parts) == 2:
            score1 = allele_activity.get(parts[0], 1.0 if "*1" in parts[0] else 0.0)
            score2 = allele_activity.get(parts[1], 1.0 if "*1" in parts[1] else 0.0)
            total_score = score1 + score2
        else:
            total_score = 2.0

        if total_score > 2.25:
            return MetabolizerPhenotype.ULTRA_RAPID
        elif 1.25 <= total_score <= 2.25:
            return MetabolizerPhenotype.NORMAL
        elif 0.0 < total_score < 1.25:
            return MetabolizerPhenotype.INTERMEDIATE
        elif total_score == 0.0:
            return MetabolizerPhenotype.POOR
        return MetabolizerPhenotype.NORMAL

    @classmethod
    def get_cyp2c9_phenotype(cls, diplotype: str) -> MetabolizerPhenotype:
        norm = cls.normalize_diplotype(diplotype)
        # *1 = Normal (1.0), *2 = Decreased (0.5), *3 = No/Minimal Function (0.0)
        if norm in ["*1/*1"]:
            return MetabolizerPhenotype.NORMAL
        if norm in ["*1/*2", "*1/*3"]:
            return MetabolizerPhenotype.INTERMEDIATE
        if norm in ["*2/*2", "*2/*3", "*3/*3"]:
            return MetabolizerPhenotype.POOR
        if "*3" in norm:
            return MetabolizerPhenotype.POOR if "*2" in norm or norm.count("*3") > 1 else MetabolizerPhenotype.INTERMEDIATE
        if "*2" in norm:
            return MetabolizerPhenotype.INTERMEDIATE
        return MetabolizerPhenotype.NORMAL

    @classmethod
    def get_dpyd_phenotype(cls, diplotype: str) -> MetabolizerPhenotype:
        norm = cls.normalize_diplotype(diplotype).lower()
        # High risk no function: *2A, *13, c.1679T>G, c.1905+1G>A, rs3918290
        # Decreased function: c.2846A>T, HapB3, rs67376798
        no_func_alleles = ["*2a", "*13", "c.1679t>g", "rs3918290", "c.1905+1g>a"]
        dec_func_alleles = ["c.2846a>t", "hapb3", "rs67376798"]

        parts = norm.split("/") if "/" in norm else [norm]
        score = 0.0
        for p in parts:
            if any(nf in p for nf in no_func_alleles):
                score += 0.0
            elif any(df in p for df in dec_func_alleles):
                score += 0.5
            else:
                score += 1.0

        if score <= 0.5:
            return MetabolizerPhenotype.POOR
        elif score < 2.0:
            return MetabolizerPhenotype.INTERMEDIATE
        return MetabolizerPhenotype.NORMAL

    @classmethod
    def get_tpmt_phenotype(cls, diplotype: str) -> MetabolizerPhenotype:
        norm = cls.normalize_diplotype(diplotype)
        # *1 normal, *2, *3A, *3B, *3C no function
        non_func = ["*2", "*3A", "*3B", "*3C", "*4"]
        has_non_func = sum(1 for nf in non_func if nf in norm)
        if has_non_func >= 2 or norm in ["*3A/*3A", "*2/*2", "*3C/*3C", "*3A/*3C"]:
            return MetabolizerPhenotype.POOR
        elif has_non_func == 1 or norm in ["*1/*2", "*1/*3A", "*1/*3C"]:
            return MetabolizerPhenotype.INTERMEDIATE
        return MetabolizerPhenotype.NORMAL


class PharmacogenomicsEngine:
    """Core Clinical Pharmacogenomics Risk Assessment & Decision Engine."""

    # Clinically verified strong enzyme inhibitors that induce phenoconversion
    POTENT_INHIBITORS = {
        "CYP2D6": ["fluoxetine", "paroxetine", "bupropion", "amiodarone", "duloxetine", "haloperidol"],
        "CYP2C19": ["omeprazole", "fluconazole", "fluvoxamine", "voriconazole", "fluoxetine"],
        "CYP2C9": ["amiodarone", "fluconazole", "capecitabine", "metronidazole"],
        "CYP3A4": ["clarithromycin", "amiodarone", "atazanavir", "fluconazole", "voriconazole"]
    }

    POTENT_INDUCERS = {
        "CYP3A4": ["rifampin", "carbamazepine", "phenytoin", "st_johns_wort"],
        "CYP2C19": ["rifampin", "carbamazepine"],
        "CYP2C9": ["rifampin", "carbamazepine"]
    }

    def __init__(self, db_path: Optional[str] = None):
        self.db = DrugDatabase(db_path)
        self.registry = AlleleRegistry()

    def resolve_patient_phenotypes(
        self, patient_genotype: Dict[str, str]
    ) -> Dict[str, MetabolizerPhenotype]:
        """Derives baseline genetic metabolizer phenotypes from patient star-alleles."""
        phenotypes: Dict[str, MetabolizerPhenotype] = {}

        if "CYP2C19" in patient_genotype:
            phenotypes["CYP2C19"] = self.registry.get_cyp2c19_phenotype(patient_genotype["CYP2C19"])

        if "CYP2D6" in patient_genotype:
            phenotypes["CYP2D6"] = self.registry.get_cyp2d6_phenotype(patient_genotype["CYP2D6"])

        if "CYP2C9" in patient_genotype:
            phenotypes["CYP2C9"] = self.registry.get_cyp2c9_phenotype(patient_genotype["CYP2C9"])

        if "DPYD" in patient_genotype:
            phenotypes["DPYD"] = self.registry.get_dpyd_phenotype(patient_genotype["DPYD"])

        if "TPMT" in patient_genotype:
            phenotypes["TPMT"] = self.registry.get_tpmt_phenotype(patient_genotype["TPMT"])

        return phenotypes

    def apply_phenoconversion(
        self,
        baseline_phenotypes: Dict[str, MetabolizerPhenotype],
        medication_keys: List[str]
    ) -> Tuple[Dict[str, MetabolizerPhenotype], List[PhenoconversionEvent]]:
        """
        Calculates functional phenocopy conversion resulting from concurrent inhibitor or inducer drugs.
        e.g., A CYP2D6 Normal Metabolizer taking Fluoxetine phenoconverts to Poor Metabolizer.
        """
        effective_phenotypes = dict(baseline_phenotypes)
        events: List[PhenoconversionEvent] = []

        # Check CYP2D6 inhibition
        cyp2d6_base = baseline_phenotypes.get("CYP2D6", MetabolizerPhenotype.NORMAL)
        if cyp2d6_base in [MetabolizerPhenotype.NORMAL, MetabolizerPhenotype.RAPID, MetabolizerPhenotype.ULTRA_RAPID]:
            for drug in medication_keys:
                if drug in self.POTENT_INHIBITORS["CYP2D6"]:
                    effective_phenotypes["CYP2D6"] = MetabolizerPhenotype.POOR
                    events.append(
                        PhenoconversionEvent(
                            gene="CYP2D6",
                            perpetrator_drug=drug.capitalize(),
                            baseline_phenotype=cyp2d6_base.value,
                            effective_phenotype=MetabolizerPhenotype.POOR.value,
                            mechanism=f"Potent competitive/mechanism-based inhibition of CYP2D6 by {drug.capitalize()} induces clinical phenocopy conversion to Poor Metabolizer."
                        )
                    )
                    break

        # Check CYP2C19 inhibition
        cyp2c19_base = baseline_phenotypes.get("CYP2C19", MetabolizerPhenotype.NORMAL)
        if cyp2c19_base in [MetabolizerPhenotype.NORMAL, MetabolizerPhenotype.RAPID, MetabolizerPhenotype.ULTRA_RAPID]:
            for drug in medication_keys:
                if drug in self.POTENT_INHIBITORS["CYP2C19"]:
                    target_phenotype = (
                        MetabolizerPhenotype.POOR
                        if drug in ["fluconazole", "fluvoxamine"]
                        else MetabolizerPhenotype.INTERMEDIATE
                    )
                    effective_phenotypes["CYP2C19"] = target_phenotype
                    events.append(
                        PhenoconversionEvent(
                            gene="CYP2C19",
                            perpetrator_drug=drug.capitalize(),
                            baseline_phenotype=cyp2c19_base.value,
                            effective_phenotype=target_phenotype.value,
                            mechanism=f"Inhibition of CYP2C19 by {drug.capitalize()} suppresses enzymatic capacity, converting patient to {target_phenotype.value} phenocopy."
                        )
                    )
                    break

        # Check CYP2C9 inhibition
        cyp2c9_base = baseline_phenotypes.get("CYP2C9", MetabolizerPhenotype.NORMAL)
        if cyp2c9_base in [MetabolizerPhenotype.NORMAL]:
            for drug in medication_keys:
                if drug in self.POTENT_INHIBITORS["CYP2C9"]:
                    effective_phenotypes["CYP2C9"] = MetabolizerPhenotype.POOR
                    events.append(
                        PhenoconversionEvent(
                            gene="CYP2C9",
                            perpetrator_drug=drug.capitalize(),
                            baseline_phenotype=cyp2c9_base.value,
                            effective_phenotype=MetabolizerPhenotype.POOR.value,
                            mechanism=f"Potent blockade of CYP2C9 by {drug.capitalize()} mimics homozygous loss-of-function phenotype."
                        )
                    )
                    break

        return effective_phenotypes, events

    def calculate_warfarin_sensitivity(
        self,
        cyp2c9_allele: Optional[str],
        vkorc1_genotype: Optional[str]
    ) -> Dict[str, Any]:
        """
        CPIC / IWPC Warfarin pharmacogenomic sensitivity algorithm.
        Estimates required maintenance dose reduction percentage and bleeding risk index.
        """
        reduction_pct = 0
        risk_level = PGxSeverity.NORMAL
        rationale = []

        # CYP2C9 factor
        if cyp2c9_allele:
            norm_cyp = AlleleRegistry.normalize_diplotype(cyp2c9_allele)
            if norm_cyp in ["*2/*3", "*3/*3"]:
                reduction_pct += 60
                risk_level = PGxSeverity.HIGH_RISK
                rationale.append("CYP2C9 *3 carrier (markedly impaired S-warfarin clearance, ~80-90% reduction)")
            elif norm_cyp in ["*2/*2", "*1/*3"]:
                reduction_pct += 35
                risk_level = PGxSeverity.HIGH_RISK
                rationale.append("CYP2C9 Intermediate Metabolizer (*1/*3 or *2/*2, moderate clearance impairment)")
            elif norm_cyp in ["*1/*2"]:
                reduction_pct += 20
                risk_level = PGxSeverity.MODERATE_RISK
                rationale.append("CYP2C9 *1/*2 (mild clearance impairment)")

        # VKORC1 factor (-1639 G>A / rs9923231)
        if vkorc1_genotype:
            v_clean = vkorc1_genotype.strip().upper().replace("RS9923231:", "").replace("-1639", "")
            if "A/A" in v_clean or "AA" in v_clean:
                reduction_pct += 45
                risk_level = PGxSeverity.HIGH_RISK
                rationale.append("VKORC1 -1639 A/A high-sensitivity genotype (suppressed vitamin K epoxide reductase synthesis)")
            elif "G/A" in v_clean or "GA" in v_clean or "A/G" in v_clean:
                reduction_pct += 25
                if risk_level != PGxSeverity.HIGH_RISK:
                    risk_level = PGxSeverity.MODERATE_RISK
                rationale.append("VKORC1 -1639 G/A intermediate sensitivity")
            elif "G/G" in v_clean or "GG" in v_clean:
                rationale.append("VKORC1 -1639 G/G wild-type / normal sensitivity")

        total_reduction = min(85, reduction_pct)
        recommended_starting_dose = round(5.0 * (1.0 - (total_reduction / 100.0)), 1)
        if recommended_starting_dose < 1.0:
            recommended_starting_dose = 1.0

        rationale_str = "; ".join(rationale) if rationale else "Standard wild-type Warfarin sensitivity."
        if total_reduction > 0:
            rationale_str += ". Marked reduction in clearance and increased INR responsiveness; elevated risk of major hemorrhagic bleeding complications."

        return {
            "risk_level": risk_level.value,
            "estimated_dose_reduction_percent": total_reduction,
            "recommended_starting_dose_mg": recommended_starting_dose,
            "clinical_rationale": rationale_str
        }

    def assess_patient_risk(
        self,
        patient_genotype: Dict[str, str],
        medications: List[str]
    ) -> Dict[str, Any]:
        """
        Comprehensive clinical audit of patient medications against patient genotype and co-medications.
        Returns validated CPIC alerts, phenoconversion records, and aggregate hazard metrics.
        """
        alerts: List[PGxAlert] = []
        contraindicated_drugs: List[str] = []

        # Canonicalize medications
        canonical_meds = []
        for m in medications:
            c = self.db.get_canonical_name(m)
            if c:
                canonical_meds.append(c)
            else:
                canonical_meds.append(m.lower().strip())

        # Determine genetic baseline and phenoconverted phenotypes
        baseline_phenotypes = self.resolve_patient_phenotypes(patient_genotype)
        effective_phenotypes, phenoconversion_events = self.apply_phenoconversion(
            baseline_phenotypes, canonical_meds
        )

        # -------------------------------------------------------------
        # 1. HLA-B*5701 & Abacavir (Fatal Hypersensitivity)
        # -------------------------------------------------------------
        hla_b5701 = patient_genotype.get("HLA-B*5701", "").strip().capitalize()
        if "abacavir" in canonical_meds:
            if hla_b5701 in ["Positive", "+", "Present", "Carrier"]:
                contraindicated_drugs.append("Abacavir")
                alerts.append(
                    PGxAlert(
                        drug="Abacavir",
                        gene="HLA-B*5701",
                        severity=PGxSeverity.CONTRAINDICATED,
                        phenotype="Carrier (Positive)",
                        alert_type="IMMUNOLOGIC_HYPERSENSITIVITY_FATALITY",
                        summary="Strictly Contraindicated: Fatal multi-organ systemic hypersensitivity reaction.",
                        clinical_implication="Abacavir binds non-covalently within the peptide-binding groove of HLA-B*57:01, altering the self-peptide repertoire and triggering an autoimmune CD8+ T-cell response with fatal anaphylactoid multi-organ collapse.",
                        recommendation="Do not initiate or immediately discontinue Abacavir. Substitute with alternative antiretroviral (e.g., Tenofovir alafenamide / Emtricitabine or Bictegravir). Record Abacavir as a permanent severe allergy.",
                        guideline_source="CPIC Level A / FDA Black Box Warning"
                    )
                )

        # -------------------------------------------------------------
        # 2. HLA-B*1502 & Carbamazepine / Oxcarbazepine (SJS / TEN)
        # -------------------------------------------------------------
        hla_b1502 = patient_genotype.get("HLA-B*1502", "").strip().capitalize()
        if any(d in canonical_meds for d in ["carbamazepine", "oxcarbazepine"]):
            drug_name = "Carbamazepine" if "carbamazepine" in canonical_meds else "Oxcarbazepine"
            if hla_b1502 in ["Positive", "+", "Present", "Carrier"]:
                contraindicated_drugs.append(drug_name)
                alerts.append(
                    PGxAlert(
                        drug=drug_name,
                        gene="HLA-B*1502",
                        severity=PGxSeverity.CONTRAINDICATED,
                        phenotype="Carrier (Positive)",
                        alert_type="SEVERE_CUTANEOUS_ADVERSE_REACTION",
                        summary=f"Strictly Contraindicated: Life-threatening Stevens-Johnson syndrome (SJS) and Toxic Epidermal Necrolysis (TEN).",
                        clinical_implication=f"{drug_name} triggers severe cytotoxic T-lymphocyte and NK-cell mediated epidermal necrosis and mucosal detachment in HLA-B*1502 positive individuals, with mortality up to 50%.",
                        recommendation=f"Contraindicated. Avoid {drug_name}. Choose an alternative anticonvulsant not associated with SJS in HLA-B*1502 (e.g., Levetiracetam, Valproate, Gabapentin).",
                        guideline_source="CPIC Level A / FDA Boxed Warning"
                    )
                )

        # -------------------------------------------------------------
        # 3. CYP2C19 & Clopidogrel (Resistance & Stent Thrombosis)
        # -------------------------------------------------------------
        cyp2c19_eff = effective_phenotypes.get("CYP2C19")
        cyp2c19_base = baseline_phenotypes.get("CYP2C19")
        is_cyp2c19_phenoconverted = cyp2c19_eff != cyp2c19_base

        if "clopidogrel" in canonical_meds and cyp2c19_eff:
            if cyp2c19_eff == MetabolizerPhenotype.POOR:
                alerts.append(
                    PGxAlert(
                        drug="Clopidogrel",
                        gene="CYP2C19",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=cyp2c19_eff.value,
                        alert_type="ANTIPLATELET_RESISTANCE_AND_THROMBOSIS",
                        summary="High Risk: Markedly diminished bioactivation; elevated cardiovascular death and stent thrombosis.",
                        clinical_implication="Clopidogrel is an inactive prodrug requiring two-step hepatic CYP2C19 oxidation to its active thiol metabolite. In Poor Metabolizers, active metabolite AUC drops by >70%, resulting in failure of platelet P2Y12 inhibition.",
                        recommendation="Avoid Clopidogrel. Prescribe alternative P2Y12 inhibitor with direct activation (Prasugrel 10 mg daily or Ticagrelor 90 mg twice daily), unless contraindicated by bleeding risk or history of stroke/TIA.",
                        guideline_source="CPIC Level A Guideline",
                        phenoconverted=is_cyp2c19_phenoconverted,
                        perpetrator_drug="Omeprazole" if "omeprazole" in canonical_meds else None
                    )
                )
            elif cyp2c19_eff == MetabolizerPhenotype.INTERMEDIATE:
                alerts.append(
                    PGxAlert(
                        drug="Clopidogrel",
                        gene="CYP2C19",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype=cyp2c19_eff.value,
                        alert_type="REDUCED_PLATELET_INHIBITION",
                        summary="Moderate Risk: Reduced active metabolite exposure and subtherapeutic platelet inhibition.",
                        clinical_implication="Intermediate metabolizers exhibit significantly lower active metabolite levels and higher on-treatment platelet reactivity compared to normal metabolizers.",
                        recommendation="Consider alternative antiplatelet therapy (Ticagrelor or Prasugrel), particularly in high-risk PCI or acute coronary syndrome (ACS) settings.",
                        guideline_source="CPIC Level A Guideline",
                        phenoconverted=is_cyp2c19_phenoconverted
                    )
                )

        # -------------------------------------------------------------
        # 4. CYP2C19 & Voriconazole (Hyper-Exposure vs Inefficacy)
        # -------------------------------------------------------------
        if "voriconazole" in canonical_meds and cyp2c19_eff:
            if cyp2c19_eff == MetabolizerPhenotype.POOR:
                alerts.append(
                    PGxAlert(
                        drug="Voriconazole",
                        gene="CYP2C19",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=cyp2c19_eff.value,
                        alert_type="NEUROTOXICITY_AND_HEPATOTOXICITY",
                        summary="High Risk: Markedly increased voriconazole concentrations; severe neurotoxicity and visual hallucinations.",
                        clinical_implication="Voriconazole clearance is decreased by up to 75% in CYP2C19 PMs, causing plasma trough levels > 5.5 mcg/mL.",
                        recommendation="Reduce dose by 50% and perform aggressive therapeutic drug monitoring (trough target 1.5-4.5 mcg/mL), or switch to Isavuconazole or Posaconazole.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )
            elif cyp2c19_eff in [MetabolizerPhenotype.RAPID, MetabolizerPhenotype.ULTRA_RAPID]:
                alerts.append(
                    PGxAlert(
                        drug="Voriconazole",
                        gene="CYP2C19",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=cyp2c19_eff.value,
                        alert_type="THERAPEUTIC_FAILURE_FUNGAL_SEPSIS",
                        summary="High Risk: Accelerated clearance leading to subtherapeutic levels and invasive fungal infection breakthrough.",
                        clinical_implication="Extensive metabolism via CYP2C19 *17 leads to failure to attain therapeutic trough (>1.5 mcg/mL).",
                        recommendation="Avoid Voriconazole for primary treatment; switch to alternative antifungal agent not heavily metabolized by CYP2C19 (e.g. Liposomal Amphotericin B or Isavuconazole).",
                        guideline_source="CPIC Level A Guideline"
                    )
                )

        # -------------------------------------------------------------
        # 5. CYP2D6 & Codeine / Tramadol (Fatal Toxicity vs Lack of Efficacy)
        # -------------------------------------------------------------
        cyp2d6_eff = effective_phenotypes.get("CYP2D6")
        cyp2d6_base = baseline_phenotypes.get("CYP2D6")
        is_cyp2d6_phenoconverted = cyp2d6_eff != cyp2d6_base

        for opioid in ["codeine", "tramadol"]:
            if opioid in canonical_meds and cyp2d6_eff:
                op_name = opioid.capitalize()
                if cyp2d6_eff == MetabolizerPhenotype.ULTRA_RAPID:
                    contraindicated_drugs.append(op_name)
                    alerts.append(
                        PGxAlert(
                            drug=op_name,
                            gene="CYP2D6",
                            severity=PGxSeverity.CONTRAINDICATED,
                            phenotype=cyp2d6_eff.value,
                            alert_type="FATAL_OPIOID_OVERDOSE_RESPIRATORY_DEPRESSION",
                            summary=f"Strictly Contraindicated: Rapid excessive conversion into active opioid metabolite; risk of fatal respiratory depression.",
                            clinical_implication=f"CYP2D6 Ultra-Rapid Metabolizers exhibit exaggerated bioactivation of {op_name} into potent active metabolites (morphine / M1), generating toxic peak concentrations even with therapeutic doses.",
                            recommendation=f"Avoid {op_name} entirely. Choose non-opioid analgesics (NSAIDs, Acetaminophen) or an opioid not reliant on CYP2D6 bioactivation (Morphine, Hydromorphone) with standard monitoring.",
                            guideline_source="CPIC Level A / FDA Black Box Warning"
                        )
                    )
                elif cyp2d6_eff == MetabolizerPhenotype.POOR:
                    alerts.append(
                        PGxAlert(
                            drug=op_name,
                            gene="CYP2D6",
                            severity=PGxSeverity.HIGH_RISK,
                            phenotype=cyp2d6_eff.value,
                            alert_type="ANALGESIC_FAILURE",
                            summary=f"High Risk: Inadequate analgesia due to absent bioactivation into active metabolite.",
                            clinical_implication=f"In Poor Metabolizers, conversion of {op_name} to active metabolite is negligible, producing inadequate pain relief despite escalating doses.",
                            recommendation=f"Avoid {op_name}. Utilize alternative analgesic not bioactivated by CYP2D6 (e.g., Morphine, Hydromorphone, Non-opioids).",
                            guideline_source="CPIC Level A Guideline",
                            phenoconverted=is_cyp2d6_phenoconverted,
                            perpetrator_drug="Fluoxetine" if "fluoxetine" in canonical_meds else None
                        )
                    )

        # -------------------------------------------------------------
        # 6. CYP2D6 & Tamoxifen (Endoxifen Deficit & Recurrence Risk)
        # -------------------------------------------------------------
        if "tamoxifen" in canonical_meds and cyp2d6_eff:
            if cyp2d6_eff == MetabolizerPhenotype.POOR:
                alerts.append(
                    PGxAlert(
                        drug="Tamoxifen",
                        gene="CYP2D6",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=cyp2d6_eff.value,
                        alert_type="BREAST_CANCER_RECURRENCE_RISK",
                        summary="High Risk: Impaired endoxifen bioactivation; increased breast cancer recurrence and decreased event-free survival.",
                        clinical_implication="Tamoxifen is a prodrug requiring CYP2D6 4-hydroxylation to endoxifen (100-fold higher affinity for estrogen receptor). Poor metabolizers achieve endoxifen concentrations < 20 nM, significantly increasing risk of cancer relapse.",
                        recommendation="Avoid Tamoxifen. In postmenopausal women, switch to an aromatase inhibitor (Anastrozole, Letrozole, Exemestane). In premenopausal women, consider GnRH agonist plus aromatase inhibitor.",
                        guideline_source="CPIC Level A Guideline",
                        phenoconverted=is_cyp2d6_phenoconverted
                    )
                )
            elif cyp2d6_eff == MetabolizerPhenotype.INTERMEDIATE:
                alerts.append(
                    PGxAlert(
                        drug="Tamoxifen",
                        gene="CYP2D6",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype=cyp2d6_eff.value,
                        alert_type="SUBOPTIMAL_ENDOXIFEN_EXPOSURE",
                        summary="Moderate Risk: Suboptimal active metabolite levels.",
                        clinical_implication="Intermediate metabolizers exhibit reduced endoxifen levels which may diminish long-term oncologic protection.",
                        recommendation="Consider aromatase inhibitor for postmenopausal patients or consider tamoxifen dose increase to 40 mg daily under oncology supervision.",
                        guideline_source="CPIC Level A Guideline",
                        phenoconverted=is_cyp2d6_phenoconverted
                    )
                )

        # -------------------------------------------------------------
        # 7. CYP2D6 & Metoprolol (Severe Bradycardia / Hypotension)
        # -------------------------------------------------------------
        if "metoprolol" in canonical_meds and cyp2d6_eff:
            if cyp2d6_eff == MetabolizerPhenotype.POOR:
                alerts.append(
                    PGxAlert(
                        drug="Metoprolol",
                        gene="CYP2D6",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype=cyp2d6_eff.value,
                        alert_type="CARDIOVASCULAR_EXPOSURE_SURGE",
                        summary="Moderate Risk: 3- to 5-fold higher metoprolol systemic exposure; profound bradycardia, heart block, and fatigue.",
                        clinical_implication="CYP2D6 mediates alpha-hydroxylation and O-demethylation of metoprolol. In Poor Metabolizers, clearance is drastically reduced.",
                        recommendation="Initiate metoprolol at 25-50% of the standard dose, or switch to beta-blockers not cleared by CYP2D6 (e.g. Atenolol, Bisoprolol, Nadolol).",
                        guideline_source="DPWG / CPIC Level B Guideline",
                        phenoconverted=is_cyp2d6_phenoconverted
                    )
                )

        # -------------------------------------------------------------
        # 8. VKORC1 & CYP2C9 & Warfarin (Hemorrhage & INR Volatility)
        # -------------------------------------------------------------
        if "warfarin" in canonical_meds:
            cyp2c9_str = patient_genotype.get("CYP2C9")
            vkorc1_str = patient_genotype.get("VKORC1")
            warfarin_calc = self.calculate_warfarin_sensitivity(cyp2c9_str, vkorc1_str)

            if warfarin_calc["estimated_dose_reduction_percent"] >= 35:
                alerts.append(
                    PGxAlert(
                        drug="Warfarin",
                        gene="CYP2C9 / VKORC1",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=f"Reduced Dose: -{warfarin_calc['estimated_dose_reduction_percent']}%",
                        alert_type="FATAL_HEMORRHAGE_HAZARD",
                        summary=f"High Risk: Profound sensitivity to Warfarin; requires {warfarin_calc['estimated_dose_reduction_percent']}% starting dose reduction to avoid fatal bleeding.",
                        clinical_implication=warfarin_calc["clinical_rationale"],
                        recommendation=f"Initiate Warfarin at {warfarin_calc['recommended_starting_dose_mg']} mg daily (baseline standard 5 mg) with frequent INR checks at days 3, 5, 7. Alternatively, evaluate DOAC (Apixaban, Rivaroxaban) if non-valvular AF.",
                        guideline_source="CPIC Level A Guideline / IWPC Algorithm"
                    )
                )
            elif warfarin_calc["estimated_dose_reduction_percent"] > 0:
                alerts.append(
                    PGxAlert(
                        drug="Warfarin",
                        gene="CYP2C9 / VKORC1",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype=f"Moderate Sensitivity: -{warfarin_calc['estimated_dose_reduction_percent']}%",
                        alert_type="ELEVATED_BLEEDING_RISK",
                        summary=f"Moderate Risk: Moderate starting dose reduction recommended ({warfarin_calc['estimated_dose_reduction_percent']}%).",
                        clinical_implication=warfarin_calc["clinical_rationale"],
                        recommendation=f"Initiate at {warfarin_calc['recommended_starting_dose_mg']} mg daily and monitor INR diligently.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )

        # -------------------------------------------------------------
        # 9. DPYD & Fluorouracil / Capecitabine (Lethal Myelosuppression)
        # -------------------------------------------------------------
        dpyd_pheno = baseline_phenotypes.get("DPYD")
        if any(d in canonical_meds for d in ["fluorouracil", "capecitabine"]) and dpyd_pheno:
            target_drug = "Fluorouracil" if "fluorouracil" in canonical_meds else "Capecitabine"
            if dpyd_pheno == MetabolizerPhenotype.POOR:
                contraindicated_drugs.append(target_drug)
                alerts.append(
                    PGxAlert(
                        drug=target_drug,
                        gene="DPYD",
                        severity=PGxSeverity.CONTRAINDICATED,
                        phenotype=dpyd_pheno.value,
                        alert_type="LETHAL_FLUOROPYRIMIDINE_TOXICITY",
                        summary="Strictly Contraindicated: Complete dihydropyrimidine dehydrogenase deficiency; life-threatening bone marrow aplasia and sepsis.",
                        clinical_implication="DPYD is responsible for >80% of 5-FU elimination. Complete deficiency causes uncontrolled fluoropyrimidine accumulation, pancytopenia, mucositis, and septic shock.",
                        recommendation=f"Strictly avoid {target_drug}. Select alternative non-fluoropyrimidine chemotherapy regimen.",
                        guideline_source="CPIC Level A / EMA Black Box Warning"
                    )
                )
            elif dpyd_pheno == MetabolizerPhenotype.INTERMEDIATE:
                alerts.append(
                    PGxAlert(
                        drug=target_drug,
                        gene="DPYD",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=dpyd_pheno.value,
                        alert_type="SEVERE_DPYD_TOXICITY_RISK",
                        summary="High Risk: Partial DPD deficiency; severe toxicities unless dose is reduced by 50%.",
                        clinical_implication="Partial deficiency results in significantly reduced clearance of 5-FU and high risk of grade 4-5 toxicities.",
                        recommendation=f"Reduce initial {target_drug} dose by 50%. Titrate subsequent doses based on toxicity and therapeutic drug monitoring.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )

        # -------------------------------------------------------------
        # 10. TPMT / NUDT15 & Mercaptopurine (Myelosuppression)
        # -------------------------------------------------------------
        tpmt_pheno = baseline_phenotypes.get("TPMT")
        if "mercaptopurine" in canonical_meds and tpmt_pheno:
            if tpmt_pheno == MetabolizerPhenotype.POOR:
                alerts.append(
                    PGxAlert(
                        drug="Mercaptopurine",
                        gene="TPMT",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype=tpmt_pheno.value,
                        alert_type="SEVERE_MYELOSUPPRESSION",
                        summary="High Risk: Deficient TPMT activity; massive thioguanine nucleotide accumulation causing lethal pancytopenia.",
                        clinical_implication="TPMT poor metabolizers shunting mercaptopurine into active cytotoxic 6-TGN metabolites, causing extreme hematopoietic toxicity.",
                        recommendation="Drastically reduce dose (starting dose 10% of standard, e.g. 10-fold reduction administered 3x/week) or select alternative immunosuppressive.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )
            elif tpmt_pheno == MetabolizerPhenotype.INTERMEDIATE:
                alerts.append(
                    PGxAlert(
                        drug="Mercaptopurine",
                        gene="TPMT",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype=tpmt_pheno.value,
                        alert_type="MODERATE_LEUKOPENIA_RISK",
                        summary="Moderate Risk: Reduced TPMT activity; heightened risk of leukopenia.",
                        clinical_implication="Intermediate metabolizers accumulate higher concentrations of cytotoxic 6-TGN.",
                        recommendation="Reduce starting dose by 30-50% and monitor complete blood count (CBC) weekly.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )

        # -------------------------------------------------------------
        # 11. SLCO1B1 & Simvastatin / Atorvastatin (Rhabdomyolysis)
        # -------------------------------------------------------------
        slco1b1_val = patient_genotype.get("SLCO1B1", "").strip().upper()
        if "simvastatin" in canonical_meds:
            if "C/C" in slco1b1_val or "*5/*5" in slco1b1_val or "521C/C" in slco1b1_val:
                alerts.append(
                    PGxAlert(
                        drug="Simvastatin",
                        gene="SLCO1B1",
                        severity=PGxSeverity.HIGH_RISK,
                        phenotype="Poor Function (*5/*5 or 521CC)",
                        alert_type="RHABDOMYOLYSIS_HAZARD",
                        summary="High Risk: >220% increase in plasma simvastatin acid AUC; high risk of severe myopathy and rhabdomyolysis.",
                        clinical_implication="OATP1B1 hepatic uptake transporter deficiency impairs hepatic clearance, dramatically raising systemic exposure.",
                        recommendation="Avoid Simvastatin doses > 20 mg/day or switch to an alternative statin with lower SLCO1B1 transporter dependence (Pravastatin, Rosuvastatin).",
                        guideline_source="CPIC Level A Guideline"
                    )
                )
            elif "T/C" in slco1b1_val or "*1/*5" in slco1b1_val or "521T/C" in slco1b1_val:
                alerts.append(
                    PGxAlert(
                        drug="Simvastatin",
                        gene="SLCO1B1",
                        severity=PGxSeverity.MODERATE_RISK,
                        phenotype="Intermediate Function (521TC)",
                        alert_type="STATIN_MYOPATHY_RISK",
                        summary="Moderate Risk: Elevated simvastatin exposure and moderate myopathy risk.",
                        clinical_implication="Heterozygous 521T>C carriers have moderately reduced OATP1B1 transport activity.",
                        recommendation="Limit Simvastatin dose to maximum 20-40 mg daily; consider Rosuvastatin or Pravastatin.",
                        guideline_source="CPIC Level A Guideline"
                    )
                )

        # -------------------------------------------------------------
        # Calculate Hazard Score & Audit Summary
        # -------------------------------------------------------------
        hazard_score = 10  # Baseline nominal
        if any(a.severity == PGxSeverity.CONTRAINDICATED for a in alerts):
            hazard_score = 99
        elif any(a.severity == PGxSeverity.HIGH_RISK for a in alerts):
            hazard_score = max(hazard_score, 88)
        elif any(a.severity == PGxSeverity.MODERATE_RISK for a in alerts):
            hazard_score = max(hazard_score, 65)

        if phenoconversion_events:
            hazard_score = min(100, hazard_score + 10)

        status = "CRITICAL_ACTION_REQUIRED" if hazard_score >= 80 else ("ELEVATED_RISK" if hazard_score >= 50 else "NOMINAL")

        return {
            "status": status,
            "overall_hazard_score": hazard_score,
            "total_alerts": len(alerts),
            "contraindicated_drugs": list(set(contraindicated_drugs)),
            "alerts": [a.to_dict() for a in alerts],
            "phenoconversion_events": [p.to_dict() for p in phenoconversion_events],
            "effective_phenotypes": {k: v.value for k, v in effective_phenotypes.items()},
            "baseline_phenotypes": {k: v.value for k, v in baseline_phenotypes.items()}
        }
