"""
Canonical HL7 FHIR R4 Longitudinal Patient Cohort Builder (`pat-001` through `pat-007`).

Combines:
- Emergency Ward patients (`pat-001` to `pat-004`) enriched with longitudinal encounters,
  triage vitals, clinical notes, lab trajectories, imaging reports, medication adherence/holds,
  and open clinical loops.
- `MedicalChartAgent` clinical cases (`pat-005` Arthur Pendelton [PAT-1001],
  `pat-006` Elena Rostova [PAT-1002], `pat-007` Marcus Vance [PAT-1003]) mapped 100% to
  standard HL7 FHIR R4 resources (`Patient`, `Encounter`, `DocumentReference`, `Condition`,
  `AllergyIntolerance`, `MedicationRequest`, `Observation`, `DiagnosticReport`, `Flag`)
  with residential 5-digit US ZIP codes for hyperlocal outbreak surveillance.
"""

from __future__ import annotations

import base64
import json
from typing import Any

# Maps legacy MedicalChartAgent IDs to canonical FHIR Patient IDs
PATIENT_ID_ALIASES: dict[str, str] = {
    "PAT-1001": "pat-005",
    "PAT-1002": "pat-006",
    "PAT-1003": "pat-007",
}

EXT_BASE = "https://ehr-chart-summary-agent.clinical.example/fhir/StructureDefinition"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _build_patient_resource(p: dict[str, Any]) -> dict[str, Any]:
    pid = p["patient_id"]
    return {
        "resourceType": "Patient",
        "id": pid,
        "identifier": [
            {"system": "https://hospital.example.org/ward-id", "value": pid},
            *(
                [{"system": "https://hospital.example.org/legacy-chart-id", "value": p["legacy_id"]}]
                if p.get("legacy_id")
                else []
            ),
        ],
        "name": [{"use": "official", "family": p["family"], "given": p["given"]}],
        "gender": p["gender"],
        "birthDate": p["birth_date"],
        "telecom": [{"system": "phone", "value": p["phone"], "use": "mobile"}],
        "generalPractitioner": [{"display": p["pcp"]}],
        "address": [
            {
                "use": "home",
                "line": [p["street"]],
                "city": p["city"],
                "state": p["state"],
                "postalCode": p["postal_code"],
                "country": "US",
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/geolocation",
                        "extension": [
                            {"url": "latitude", "valueDecimal": p["lat"]},
                            {"url": "longitude", "valueDecimal": p["lon"]},
                        ],
                    }
                ],
            }
        ],
        "extension": [
            {"url": f"{EXT_BASE}/swimlane-headline", "valueString": p["swimlane_headline"]},
            {"url": f"{EXT_BASE}/swimlane-json", "valueString": json.dumps(p["swimlane"])},
        ],
    }


RAW_COHORT_SPECS: list[dict[str, Any]] = [
    # =========================================================================
    # pat-001: Alex Jordan Conn (Boston, MA 02118)
    # =========================================================================
    {
        "patient_id": "pat-001",
        "given": ["Alex", "Jordan"],
        "family": "Conn",
        "gender": "male",
        "birth_date": "1978-05-14",
        "phone": "617-555-0142",
        "pcp": "Dr. Elisha Conn, MD",
        "street": "742 Tremont St",
        "city": "Boston",
        "state": "Massachusetts",
        "postal_code": "02118",
        "lat": 42.3398,
        "lon": -71.0765,
        "todays_triage": {
            "encounter_id": "enc-pat001-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward Acute Triage",
            "chief_complaint": "Acute shortness of breath, expiratory wheezing, and persistent dry cough for 3 days.",
            "vitals": {
                "bp": "152/94 mmHg",
                "hr": "104 bpm",
                "rr": "24 /min",
                "spo2": "91% on room air",
                "temp": "100.2 F",
                "weight_lbs": 182.0,
                "bmi": 26.9,
            },
            "ma_intake_note": (
                "Patient arrived in mild-to-moderate respiratory distress speaking in 4-5 word phrases. "
                "Reports worsening dry cough since Lisinopril dose was increased last month, plus taking OTC Tylenol "
                "alongside leftover Acetaminophen chewables at home for low-grade fever."
            ),
        },
        "allergies": [
            {
                "id": "allergy-ma-sulfa",
                "substance": "Sulfonamide antibiotics",
                "reaction": "Severe urticaria and facial angioedema",
                "criticality": "high",
                "severity": "severe",
            }
        ],
        "conditions": [
            {
                "id": "cond-ma-active-asthma",
                "status": "active",
                "snomed": "195967001",
                "icd10": "J45.41",
                "display": "Moderate persistent asthma with acute exacerbation",
                "onset": "2018-11-02T11:30:00+00:00",
            },
            {
                "id": "cond-ma-active-htn",
                "status": "active",
                "snomed": "59621000",
                "icd10": "I10",
                "display": "Essential hypertension",
                "onset": "2021-03-10T09:00:00+00:00",
            },
            {
                "id": "cond-ma-prev-strep",
                "status": "resolved",
                "snomed": "43878008",
                "icd10": "J02.0",
                "display": "Streptococcal sore throat",
                "onset": "2024-07-10T10:00:00+00:00",
                "abatement": "2024-07-20T10:00:00+00:00",
            },
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat001-pcp",
                "doc_id": "doc-pat001-pcp",
                "class_code": "AMB",
                "date": "2026-10-08",
                "type": "Outpatient Primary Care Hypertension Visit",
                "facility": "Boston Medical Associates",
                "author": "Dr. Elisha Conn, MD",
                "primary_diagnosis": "Uncontrolled Essential Hypertension; Persistent Dry Cough",
                "summary_note": (
                    "48M with asthma and hypertension; home BP averaging 148/92. Up-titrated Lisinopril from 5mg to "
                    "10mg PO daily. Patient mentioned occasional throat tickle; advised to return immediately if dry "
                    "cough worsens or any lip/tongue swelling develops (ACE-inhibitor cough vs. angioedema). "
                    "Spirometry scheduled with Pulmonology on 2026-10-28."
                ),
            },
            {
                "id": "enc-pat001-ed24",
                "doc_id": "doc-pat001-ed24",
                "class_code": "EMER",
                "date": "2024-07-10",
                "type": "Urgent Care / ED Visit Note",
                "facility": "Massachusetts General Urgent Care",
                "author": "Dr. Rebecca Lin, MD",
                "primary_diagnosis": "Acute Group A Streptococcal Pharyngitis",
                "summary_note": (
                    "Rapid strep antigen positive. Given Sulfonamide allergy, treated with 10-day course of Augmentin "
                    "875/125 mg BID and PRN Acetaminophen. Resolved without complication."
                ),
            },
        ],
        "medications": [
            {
                "id": "med-ma-active-lisinopril",
                "status": "active",
                "rxcui": "314076",
                "coding_display": "Lisinopril 10 MG Oral Tablet",
                "text": "Lisinopril 10 MG Oral Tablet",
                "authored_on": "2026-10-08T10:00:00+00:00",
                "dosage": "10 mg PO once daily",
                "prior_dose": "5 mg PO once daily (increased 2026-10-08)",
                "change_type": "DOSE INCREASED on 2026-10-08",
                "adherence": "Adherent; experiencing worsening dry cough & dyspnea since up-titration.",
                "prescriber": "Dr. Elisha Conn, MD",
            },
            {
                "id": "med-ma-active-tylenol",
                "status": "active",
                "rxcui": "202433",
                "coding_display": "Tylenol",
                "text": "Tylenol 500 MG Oral Tablet",
                "authored_on": "2026-11-09T09:15:00+00:00",
                "dosage": "1000 mg (2 tablets) PO every 6 hours PRN fever/cough",
                "prior_dose": "None",
                "change_type": "RECENT OTC/PRN USE x3 days",
                "adherence": "DUPLICATE INGREDIENT WARNING: Taking 4g/day Tylenol PLUS leftover generic Acetaminophen chewables.",
                "prescriber": "Dr. Elisha Conn, MD",
            },
            {
                "id": "med-ma-prev-acetaminophen",
                "status": "stopped",
                "rxcui": "313820",
                "coding_display": "Acetaminophen 160 MG Chewable Tablet",
                "text": "Acetaminophen 160 MG Chewable Tablet",
                "authored_on": "2024-07-13T14:21:23+00:00",
                "dosage": "Stopped in EHR, but patient reports taking leftover tablets at home alongside Tylenol.",
                "prior_dose": "320 mg PRN",
                "reason": "Completed prior acute illness course; risk of accidental supratherapeutic acetaminophen dosing.",
                "reinitiation_criteria": "Discontinue leftover supply immediately to prevent hepatotoxicity.",
                "prescriber": "Dr. Elisha Conn, MD",
            },
            {
                "id": "med-ma-prev-augmentin",
                "status": "completed",
                "rxcui": "151392",
                "coding_display": "Augmentin",
                "text": "Augmentin 875 MG / 125 MG Oral Tablet",
                "authored_on": "2024-07-10T10:15:00+00:00",
                "dosage": "1 tablet PO BID for 10 days (completed)",
                "prior_dose": "875/125 mg PO BID",
                "reason": "Completed 10-day course for Streptococcal pharyngitis.",
                "reinitiation_criteria": "Completed as scheduled.",
                "prescriber": "Dr. Rebecca Lin, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat001-eos",
                "loinc": "711-2",
                "test": "Blood Eosinophils (cells/uL)",
                "unit": "cells/uL",
                "ref_range": "0 - 300",
                "history": [
                    {"date": "2025-11-14", "value": 180, "flag": "N", "context": "Annual Baseline"},
                    {"date": "2026-10-08", "value": 340, "flag": "H", "context": "PCP Visit"},
                    {"date": "2026-11-12", "value": 520, "flag": "HH", "context": "ED Triage STAT CBC (Eosinophilic Asthma Flare)"},
                ],
            },
            {
                "id_prefix": "lab-pat001-alt",
                "loinc": "1742-6",
                "test": "ALT (U/L)",
                "unit": "U/L",
                "ref_range": "7 - 35",
                "history": [
                    {"date": "2026-10-08", "value": 22, "flag": "N", "context": "Baseline LFT"},
                    {"date": "2026-11-12", "value": 58, "flag": "H", "context": "ED STAT CMP (Mild elevation after duplicate Acetaminophen/Tylenol)"},
                ],
            },
            {
                "id_prefix": "lab-pat001-pef",
                "loinc": "19935-6",
                "test": "Peak Expiratory Flow (% Predicted)",
                "unit": "%",
                "ref_range": "80 - 100",
                "history": [
                    {"date": "2025-11-14", "value": 88, "flag": "N", "context": "Outpatient Asthma Baseline"},
                    {"date": "2026-11-12", "value": 54, "flag": "LL", "context": "ED Arrival (Moderate-Severe Bronchospasm)"},
                ],
            },
        ],
        "imaging": [
            {
                "id": "img-pat001-cxr",
                "date": "2026-11-12",
                "category": "RAD",
                "modality": "Portable Chest X-Ray (ED)",
                "findings": "Hyperinflated lung fields consistent with acute asthma bronchospasm; no focal lobar consolidation or pneumothorax.",
            }
        ],
        "open_loops": [
            {
                "id": "flag-pat001-1",
                "item_id": "OPEN-001",
                "priority": "CRITICAL",
                "category": "ACE-Inhibitor Cough / Bronchospasm & Duplicate Acetaminophen Alert",
                "details": "Lisinopril up-titration (10/08) coincides with persistent dry cough & acute asthma flare (PEF 54%); patient also taking duplicate brand Tylenol + generic Acetaminophen (ALT 58 U/L). Consider switching Lisinopril to ARB (Losartan) and checking serum acetaminophen level.",
            },
            {
                "id": "flag-pat001-2",
                "item_id": "OPEN-002",
                "priority": "HIGH",
                "category": "Missed Outpatient Pulmonology Spirometry & ICS Controller Gap",
                "details": "Missed 2026-10-28 Pulmonology spirometry visit; currently has no active inhaled corticosteroid (ICS) controller prescribed despite moderate persistent asthma.",
            },
        ],
        "swimlane_headline": "Acute Asthma Flare (PEF 54%) + Lisinopril Up-Titration Cough & Duplicate Brand/Generic Acetaminophen Exposure",
        "swimlane": {
            "age_sex": "48yo Male",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2024-07-10",
                    "display_date": "Jul 10, 2024",
                    "phase": "Prior Urgent Care",
                    "tracks": {
                        "track_1_encounters": {"node_id": "A1_1", "title": "Urgent Care Strep Visit", "badge": "RESOLVED", "severity": "normal", "summary": "Group A Strep pharyngitis treated safely.", "details": "Sulfa allergy documented; treated with beta-lactam."},
                        "track_2_medications": {"node_id": "A1_2", "title": "Augmentin + Acetaminophen", "badge": "COMPLETED", "severity": "info", "summary": "Completed Augmentin; kept leftover Acetaminophen.", "details": "Leftover Acetaminophen chewables remained at home."},
                        "track_3_diagnostics": {"node_id": "A1_3", "title": "Rapid Strep (+), PEF 88%", "badge": "BASELINE", "severity": "normal", "summary": "Baseline Peak Flow 88% predicted; Eos 180.", "details": "Stable baseline pulmonary function."},
                        "track_4_open_loops": {"node_id": "A1_4", "title": "Sulfa Allergy Flagged", "badge": "ALLERGY", "severity": "info", "summary": "High-criticality Sulfonamide allergy recorded.", "details": "Avoid TMP-SMX and sulfonamide derivatives."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-10-08",
                    "display_date": "Oct 08, 2026",
                    "phase": "PCP HTN Titration",
                    "tracks": {
                        "track_1_encounters": {"node_id": "A2_1", "title": "PCP HTN Visit", "badge": "OUTPATIENT", "severity": "info", "summary": "BP 148/92; mild throat tickle noted.", "details": "Spirometry ordered for 10/28 (later missed)."},
                        "track_2_medications": {"node_id": "A2_2", "title": "Lisinopril ↑ 5mg → 10mg", "badge": "DOSE UP", "severity": "warning", "summary": "Lisinopril doubled despite early dry cough.", "details": "No ICS asthma controller on active med list."},
                        "track_3_diagnostics": {"node_id": "A2_3", "title": "Eos 340 [H] | ALT 22 [N]", "badge": "RISING EOS", "severity": "warning", "summary": "Eosinophils crept up to 340 cells/uL; ALT normal.", "details": "Early airway inflammation prior to acute flare."},
                        "track_4_open_loops": {"node_id": "A2_4", "title": "Missed 10/28 Spirometry", "badge": "CARE GAP", "severity": "warning", "summary": "No-show to Pulmonology PFTs; no ICS controller.", "details": "OPEN-002 controller therapy gap."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (ED Today)",
                    "phase": "ED Acute Dyspnea",
                    "tracks": {
                        "track_1_encounters": {"node_id": "A3_1", "title": "ED Triage: SpO2 91%, RR 24", "badge": "ED ACUTE", "severity": "critical", "summary": "Acute dyspnea, wheezing & 3-day fever/cough.", "details": "BP 152/94, HR 104, Temp 100.2 F in Boston ZIP 02118."},
                        "track_2_medications": {"node_id": "A3_2", "title": "Tylenol + Acetaminophen Overlap", "badge": "DUPLICATE", "severity": "critical", "summary": "Taking Tylenol 4g/d + leftover Acetaminophen + Lisinopril.", "details": "Brand + Generic duplicate active ingredient + ACEi cough."},
                        "track_3_diagnostics": {"node_id": "A3_3", "title": "PEF 54% [LL] | Eos 520 | ALT 58", "badge": "CRITICAL", "severity": "critical", "summary": "CXR hyperinflated; Eos 520 [HH]; ALT rose 22 → 58.", "details": "Acute bronchospasm + mild transaminitis."},
                        "track_4_open_loops": {"node_id": "A3_4", "title": "OPEN-001 & OPEN-002 Action", "badge": "ACTION", "severity": "critical", "summary": "Nebulizers/steroids, stop duplicate APAP, switch ACEi→ARB.", "details": "Start ICS controller prior to ED discharge."},
                    },
                },
            ],
            "causal_links": [
                {"from": "A2_2", "to": "A3_1", "label": "Lisinopril increase to 10mg worsened bradykinin cough alongside unmedicated eosinophilic asthma"},
                {"from": "A1_2", "to": "A3_2", "label": "Leftover generic Acetaminophen combined with OTC brand Tylenol caused supratherapeutic APAP intake"},
                {"from": "A3_2", "to": "A3_3", "label": "Duplicate acetaminophen exposure elevated ALT from 22 to 58 U/L"},
            ],
        },
    },

    # =========================================================================
    # pat-002: Maria Elena Reynolds (Portland, OR 97205)
    # =========================================================================
    {
        "patient_id": "pat-002",
        "given": ["Maria", "Elena"],
        "family": "Reynolds",
        "gender": "female",
        "birth_date": "1964-09-22",
        "phone": "503-555-0198",
        "pcp": "Dr. Sarah Jenkins, MD",
        "street": "1220 SW Morrison St",
        "city": "Portland",
        "state": "Oregon",
        "postal_code": "97205",
        "lat": 45.5202,
        "lon": -122.6844,
        "todays_triage": {
            "encounter_id": "enc-pat002-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward Acute Triage",
            "chief_complaint": "Proximal muscle weakness, dark tea-colored urine, dizziness, and fatigue x4 days.",
            "vitals": {
                "bp": "112/68 mmHg",
                "hr": "96 bpm",
                "rr": "18 /min",
                "spo2": "97% on room air",
                "temp": "98.8 F",
                "weight_lbs": 158.0,
                "bmi": 27.1,
            },
            "ma_intake_note": (
                "62F reports bilateral thigh aching and dark urine starting 1 week after Urgent Care prescribed "
                "Clarithromycin for sinusitis while she continued taking her nightly Lipitor 20mg and Metformin ER."
            ),
        },
        "allergies": [
            {
                "id": "allergy-or-latex",
                "substance": "Latex",
                "reaction": "Contact dermatitis",
                "criticality": "low",
                "severity": "mild",
            }
        ],
        "conditions": [
            {
                "id": "cond-or-active-t2d",
                "status": "active",
                "snomed": "44054006",
                "icd10": "E11.9",
                "display": "Type 2 diabetes mellitus",
                "onset": "2019-06-15T08:00:00+00:00",
            },
            {
                "id": "cond-or-active-hld",
                "status": "active",
                "snomed": "55822004",
                "icd10": "E78.5",
                "display": "Hyperlipidemia",
                "onset": "2020-03-10T08:00:00+00:00",
            },
            {
                "id": "cond-or-prev-pneumonia",
                "status": "resolved",
                "snomed": "233604007",
                "icd10": "J18.9",
                "display": "Community-acquired pneumonia",
                "onset": "2023-12-04T08:00:00+00:00",
                "abatement": "2023-12-21T08:00:00+00:00",
            },
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat002-uc",
                "doc_id": "doc-pat002-uc",
                "class_code": "AMB",
                "date": "2026-11-02",
                "type": "Walk-In Urgent Care Visit",
                "facility": "Portland Metro Urgent Care",
                "author": "Dr. Alan Cho, MD",
                "primary_diagnosis": "Acute Bacterial Rhinosinusitis",
                "summary_note": (
                    "Prescribed Clarithromycin 500mg PO BID x7 days. Outside EHR did not reconcile patient's chronic "
                    "Lipitor (Atorvastatin, CYP3A4 substrate) — Lipitor was NOT held during macrolide therapy."
                ),
            },
            {
                "id": "enc-pat002-hosp23",
                "doc_id": "doc-pat002-hosp23",
                "class_code": "IMP",
                "date": "2023-12-04",
                "type": "Inpatient Discharge Summary",
                "facility": "Oregon Health Regional Hospital",
                "author": "Dr. Sarah Jenkins, MD",
                "primary_diagnosis": "Right Lower Lobe Community-Acquired Pneumonia",
                "summary_note": "Treated with Azithromycin + Ceftriaxone; full clinical recovery.",
            },
        ],
        "medications": [
            {
                "id": "med-or-active-lipitor",
                "status": "active",
                "rxcui": "153165",
                "coding_display": "Lipitor",
                "text": "Lipitor 20 MG Oral Tablet",
                "authored_on": "2025-02-10T11:30:00+00:00",
                "dosage": "20 mg PO nightly",
                "prior_dose": "20 mg PO nightly",
                "change_type": "SEVERE CYP3A4 INTERACTION w/ recent Clarithromycin",
                "adherence": "Continued nightly through Clarithromycin course — now has severe myalgias & CK 4,850 U/L.",
                "prescriber": "Dr. Sarah Jenkins, MD",
            },
            {
                "id": "med-or-active-metformin",
                "status": "active",
                "rxcui": "860975",
                "coding_display": "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet",
                "text": "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet",
                "authored_on": "2024-11-01T09:00:00+00:00",
                "dosage": "500 mg PO once daily with evening meal",
                "prior_dose": "500 mg PO daily",
                "change_type": "HOLD RECOMMENDED IN ED (acute pigment AKI Cr 1.9)",
                "adherence": "Adherent; took last dose yesterday evening.",
                "prescriber": "Dr. Sarah Jenkins, MD",
            },
            {
                "id": "med-or-prev-azithromycin",
                "status": "stopped",
                "rxcui": "18631",
                "coding_display": "Azithromycin",
                "text": "Azithromycin 250 MG Oral Tablet",
                "authored_on": "2023-12-04T09:00:00+00:00",
                "dosage": "5-day course completed in 2023",
                "prior_dose": "250 mg PO",
                "reason": "Completed CAP antibiotic course.",
                "reinitiation_criteria": "Completed.",
                "prescriber": "Dr. Sarah Jenkins, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat002-ck",
                "loinc": "2157-6",
                "test": "Creatine Kinase / CK (U/L)",
                "unit": "U/L",
                "ref_range": "30 - 190",
                "history": [
                    {"date": "2026-03-15", "value": 110, "flag": "N", "context": "Baseline on Lipitor"},
                    {"date": "2026-11-12", "value": 4850, "flag": "HH (Critical)", "context": "ED Arrival (Statin + Clarithromycin Rhabdomyolysis)"},
                ],
            },
            {
                "id_prefix": "lab-pat002-cr",
                "loinc": "2160-0",
                "test": "Serum Creatinine (mg/dL)",
                "unit": "mg/dL",
                "ref_range": "0.6 - 1.1",
                "history": [
                    {"date": "2026-03-15", "value": 0.85, "flag": "N", "context": "Outpatient Baseline"},
                    {"date": "2026-11-12", "value": 1.92, "flag": "HH", "context": "ED Arrival (Acute Myoglobinuric AKI)"},
                ],
            },
        ],
        "imaging": [
            {
                "id": "img-pat002-us",
                "date": "2026-11-12",
                "category": "RAD",
                "modality": "Renal Ultrasound (ED)",
                "findings": "Increased bilateral renal cortical echogenicity without hydronephrosis, consistent with acute medical renal injury.",
            }
        ],
        "open_loops": [
            {
                "id": "flag-pat002-1",
                "item_id": "OPEN-011",
                "priority": "CRITICAL",
                "category": "Statin Rhabdomyolysis & Acute Kidney Injury — Hold Lipitor & Metformin",
                "details": "CK 4,850 U/L and Cr rose 0.85 -> 1.92 mg/dL after outside Clarithromycin inhibited Lipitor metabolism. Immediately HOLD Lipitor and Metformin (lactic acidosis risk in AKI) and initiate IV crystalloid hydration.",
            }
        ],
        "swimlane_headline": "CYP3A4 Statin-Macrolide Rhabdomyolysis (CK 4,850) & Myoglobinuric AKI Requiring Immediate Lipitor + Metformin Hold",
        "swimlane": {
            "age_sex": "62yo Female",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2026-03-15",
                    "display_date": "Mar 15, 2026",
                    "phase": "Outpatient Baseline",
                    "tracks": {
                        "track_1_encounters": {"node_id": "B1_1", "title": "PCP Chronic Care Visit", "badge": "STABLE", "severity": "normal", "summary": "T2DM & HLD well controlled.", "details": "Dr. S. Jenkins routine follow-up."},
                        "track_2_medications": {"node_id": "B1_2", "title": "Lipitor 20mg + Metformin ER", "badge": "ADHERENT", "severity": "normal", "summary": "Tolerating Lipitor 20mg & Metformin 500mg ER.", "details": "No muscle symptoms at baseline."},
                        "track_3_diagnostics": {"node_id": "B1_3", "title": "CK 110 [N] | Cr 0.85 [N]", "badge": "BASELINE", "severity": "normal", "summary": "Normal renal function and normal CK.", "details": "Baseline eGFR > 75."},
                        "track_4_open_loops": {"node_id": "B1_4", "title": "Routine Monitoring", "badge": "OK", "severity": "normal", "summary": "Annual labs normal.", "details": "No active safety flags."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-11-02",
                    "display_date": "Nov 02, 2026",
                    "phase": "Outside Urgent Care",
                    "tracks": {
                        "track_1_encounters": {"node_id": "B2_1", "title": "Urgent Care Sinusitis Visit", "badge": "OUTSIDE UC", "severity": "warning", "summary": "Outside clinic treated acute sinusitis.", "details": "Medication list not reconciled with PCP EHR."},
                        "track_2_medications": {"node_id": "B2_2", "title": "Clarithromycin Added onto Lipitor", "badge": "CYP3A4 DDI", "severity": "critical", "summary": "Strong CYP3A4 inhibitor started without holding Lipitor.", "details": "Markedly elevates plasma atorvastatin levels."},
                        "track_3_diagnostics": {"node_id": "B2_3", "title": "No Baseline Labs Checked", "badge": "UNMONITORED", "severity": "info", "summary": "Progressive myocyte breakdown over 10 days.", "details": "Thigh myalgias began 11/08."},
                        "track_4_open_loops": {"node_id": "B2_4", "title": "Unreconciled Outside Rx", "badge": "GAP", "severity": "warning", "summary": "No statin hold instruction given.", "details": "Preventable DDI gap."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (ED Today)",
                    "phase": "ED Rhabdomyolysis",
                    "tracks": {
                        "track_1_encounters": {"node_id": "B3_1", "title": "ED Triage: Dark Urine & Weakness", "badge": "ED ACUTE", "severity": "critical", "summary": "BP 112/68, HR 96; proximal weakness x4d.", "details": "Portland ZIP 97205."},
                        "track_2_medications": {"node_id": "B3_2", "title": "HOLD Lipitor & Metformin STAT", "badge": "HOLD BOTH", "severity": "critical", "summary": "Stop Lipitor immediately; hold Metformin in AKI.", "details": "Aggressive IV fluids initiated."},
                        "track_3_diagnostics": {"node_id": "B3_3", "title": "CK 4,850 [HH] | Cr 1.92 [HH]", "badge": "CRITICAL", "severity": "critical", "summary": "Rhabdomyolysis + acute pigment nephropathy.", "details": "Renal US excludes obstruction."},
                        "track_4_open_loops": {"node_id": "B3_4", "title": "OPEN-011 Inpatient Hydration", "badge": "CRITICAL", "severity": "critical", "summary": "Serial CK/BMP q6h; hold Metformin until eGFR > 45.", "details": "Switch to pravastatin/rosuvastatin post-recovery."},
                    },
                },
            ],
            "causal_links": [
                {"from": "B2_2", "to": "B3_3", "label": "Clarithromycin CYP3A4 inhibition of Lipitor triggered rhabdomyolysis (CK 4,850) and AKI (Cr 1.92)"},
                {"from": "B3_3", "to": "B3_2", "label": "Acute kidney injury (Cr 1.92) requires immediate temporary hold of Metformin to prevent lactic acidosis"},
            ],
        },
    },

    # =========================================================================
    # pat-003: David Raj Patel (San Francisco, CA 94108)
    # =========================================================================
    {
        "patient_id": "pat-003",
        "given": ["David", "Raj"],
        "family": "Patel",
        "gender": "male",
        "birth_date": "1985-01-30",
        "phone": "415-555-0173",
        "pcp": "Dr. Marcus Vance, MD",
        "street": "450 Sutter St",
        "city": "San Francisco",
        "state": "California",
        "postal_code": "94108",
        "lat": 37.7895,
        "lon": -122.4083,
        "todays_triage": {
            "encounter_id": "enc-pat003-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward Acute Triage",
            "chief_complaint": "Severe burning epigastric pain, melena (black tarry stools) x2 days, and orthostatic lightheadedness.",
            "vitals": {
                "bp": "98/62 mmHg",
                "hr": "114 bpm",
                "rr": "20 /min",
                "spo2": "95% on room air",
                "temp": "98.4 F",
                "weight_lbs": 168.0,
                "bmi": 24.8,
            },
            "ma_intake_note": (
                "41M tachycardic (HR 114) and hypotensive (BP 98/62). Reports taking 2-3 tablets of Advil 200mg "
                "four times daily for 3 weeks for shoulder strain after stopping Prilosec earlier."
            ),
        },
        "allergies": [],
        "conditions": [
            {
                "id": "cond-ca-active-copd",
                "status": "active",
                "snomed": "13645005",
                "icd10": "J44.9",
                "display": "Chronic obstructive lung disease (COPD)",
                "onset": "2022-04-12T10:00:00+00:00",
            },
            {
                "id": "cond-ca-prev-gerd",
                "status": "resolved",
                "snomed": "235595009",
                "icd10": "K21.9",
                "display": "Gastroesophageal reflux disease (GERD)",
                "onset": "2020-08-01T10:00:00+00:00",
                "abatement": "2023-05-15T10:00:00+00:00",
            },
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat003-ortho",
                "doc_id": "doc-pat003-ortho",
                "class_code": "AMB",
                "date": "2026-10-20",
                "type": "Outpatient Sports Medicine Visit",
                "facility": "Bay Area Orthopedics",
                "author": "Dr. Marcus Vance, MD",
                "primary_diagnosis": "Right Rotator Cuff Tendinopathy",
                "summary_note": "Advised short-term Advil PRN; patient self-escalated to 2,400 mg/day without gastroprotection.",
            }
        ],
        "medications": [
            {
                "id": "med-ca-active-advil",
                "status": "active",
                "rxcui": "153010",
                "coding_display": "Advil",
                "text": "Advil 200 MG Oral Tablet",
                "authored_on": "2026-10-20T14:00:00+00:00",
                "dosage": "1-2 tablets q6h PRN (patient taking 2,400 mg/day)",
                "prior_dose": "None",
                "change_type": "SELF-ESCALATED HIGH-DOSE NSAID -> ACUTE UGIB",
                "adherence": "Taking 12 tablets/day without PPI; STOP IMMEDIATELY.",
                "prescriber": "Dr. Marcus Vance, MD",
            },
            {
                "id": "med-ca-active-albuterol",
                "status": "active",
                "rxcui": "435",
                "coding_display": "Albuterol",
                "text": "Albuterol 90 MCG/ACTUAT Metered Dose Inhaler",
                "authored_on": "2024-09-10T11:00:00+00:00",
                "dosage": "2 puffs q4-6h PRN shortness of breath",
                "prior_dose": "2 puffs PRN",
                "change_type": "UNCHANGED",
                "adherence": "Adherent.",
                "prescriber": "Dr. Marcus Vance, MD",
            },
            {
                "id": "med-ca-prev-omeprazole",
                "status": "stopped",
                "rxcui": "203344",
                "coding_display": "Prilosec",
                "text": "Prilosec 20 MG Delayed Release Oral Capsule",
                "authored_on": "2021-01-12T09:30:00+00:00",
                "dosage": "20 mg PO daily (stopped 2023)",
                "prior_dose": "20 mg PO daily",
                "reason": "Stopped when GERD symptoms subsided; left gastric mucosa unprotected during high-dose NSAID use.",
                "reinitiation_criteria": "Initiate high-dose IV Pantoprazole immediately for acute upper GI bleed.",
                "prescriber": "Dr. Marcus Vance, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat003-hgb",
                "loinc": "718-7",
                "test": "Hemoglobin (g/dL)",
                "unit": "g/dL",
                "ref_range": "13.5 - 17.5",
                "history": [
                    {"date": "2026-04-18", "value": 14.6, "flag": "N", "context": "Outpatient Baseline"},
                    {"date": "2026-11-12", "value": 8.4, "flag": "LL (Critical)", "context": "ED Arrival (Acute NSAID Peptic Ulcer Bleed)"},
                ],
            },
            {
                "id_prefix": "lab-pat003-bun",
                "loinc": "3094-0",
                "test": "BUN (mg/dL)",
                "unit": "mg/dL",
                "ref_range": "7 - 20",
                "history": [
                    {"date": "2026-04-18", "value": 14, "flag": "N", "context": "Outpatient Baseline"},
                    {"date": "2026-11-12", "value": 46, "flag": "HH", "context": "ED Arrival (Elevated BUN/Cr ratio = Upper GI Bleed)"},
                ],
            },
        ],
        "imaging": [
            {
                "id": "img-pat003-upright",
                "date": "2026-11-12",
                "category": "RAD",
                "modality": "Upright Chest / Abdominal Radiograph (ED)",
                "findings": "No subdiaphragmatic free air to suggest perforation; emergent GI consult for EGD requested.",
            }
        ],
        "open_loops": [
            {
                "id": "flag-pat003-1",
                "item_id": "OPEN-021",
                "priority": "CRITICAL",
                "category": "Acute Upper GI Hemorrhage (Hgb 14.6 -> 8.4 g/dL) from High-Dose Advil",
                "details": "Discontinue Advil permanently, administer IV Pantoprazole bolus + infusion, type & crossmatch 2u pRBC, and emergent Gastroenterology consult for EGD.",
            }
        ],
        "swimlane_headline": "Acute NSAID-Induced Upper GI Bleed (Hgb 14.6 → 8.4 g/dL, BP 98/62) After Unprotected High-Dose Advil",
        "swimlane": {
            "age_sex": "41yo Male",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2026-04-18",
                    "display_date": "Apr 18, 2026",
                    "phase": "Baseline",
                    "tracks": {
                        "track_1_encounters": {"node_id": "C1_1", "title": "Annual PCP Checkup", "badge": "STABLE", "severity": "normal", "summary": "COPD stable; prior GERD asymptomatic.", "details": "Off PPI since 2023."},
                        "track_2_medications": {"node_id": "C1_2", "title": "Albuterol PRN; Prilosec Stopped", "badge": "NO PPI", "severity": "info", "summary": "No gastroprotective PPI active.", "details": "Prilosec discontinued previously."},
                        "track_3_diagnostics": {"node_id": "C1_3", "title": "Hgb 14.6 [N] | BUN 14 [N]", "badge": "BASELINE", "severity": "normal", "summary": "Normal baseline hemoglobin.", "details": "Cr 0.9 mg/dL."},
                        "track_4_open_loops": {"node_id": "C1_4", "title": "History of GERD", "badge": "CONTEXT", "severity": "info", "summary": "Susceptible to mucosal injury if given NSAIDs.", "details": "Needs PPI co-prescription if NSAIDs used."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-10-20",
                    "display_date": "Oct 20, 2026",
                    "phase": "NSAID Escalation",
                    "tracks": {
                        "track_1_encounters": {"node_id": "C2_1", "title": "Ortho Visit: Shoulder Strain", "badge": "OUTPATIENT", "severity": "info", "summary": "Rotator cuff tendinopathy.", "details": "Recommended short PRN ibuprofen."},
                        "track_2_medications": {"node_id": "C2_2", "title": "Advil Self-Escalated 2,400mg/d", "badge": "HIGH NSAID", "severity": "critical", "summary": "12 tabs/day Advil x3 wks without PPI.", "details": "Prostaglandin inhibition eroded gastric mucosa."},
                        "track_3_diagnostics": {"node_id": "C2_3", "title": "Occult Mucosal Erosion", "badge": "UNMONITORED", "severity": "warning", "summary": "Progressive epigastric burning -> melena.", "details": "2 days of tarry stools."},
                        "track_4_open_loops": {"node_id": "C2_4", "title": "Unprotected High-Dose NSAID", "badge": "RISK", "severity": "warning", "summary": "No PPI gastroprotection.", "details": "High UGIB risk."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (ED Today)",
                    "phase": "ED Acute UGIB",
                    "tracks": {
                        "track_1_encounters": {"node_id": "C3_1", "title": "ED Triage: BP 98/62, HR 114", "badge": "HEMODYNAMIC", "severity": "critical", "summary": "Melena & orthostasis in SF ZIP 94108.", "details": "2 large-bore IVs placed."},
                        "track_2_medications": {"node_id": "C3_2", "title": "STOP Advil → IV Pantoprazole", "badge": "STAT IV PPI", "severity": "critical", "summary": "Permanent NSAID ban + IV Pantoprazole.", "details": "Hold any antiplatelets."},
                        "track_3_diagnostics": {"node_id": "C3_3", "title": "Hgb 8.4 [LL] | BUN 46 [HH]", "badge": "CRITICAL", "severity": "critical", "summary": "6.2 g/dL Hgb drop; upright CXR no free air.", "details": "Consistent with brisk peptic ulcer bleed."},
                        "track_4_open_loops": {"node_id": "C3_4", "title": "OPEN-021 Emergent GI EGD", "badge": "CRITICAL", "severity": "critical", "summary": "Type & crossmatch + emergent EGD + H. pylori test.", "details": "ICU/step-down admission."},
                    },
                },
            ],
            "causal_links": [
                {"from": "C1_2", "to": "C2_2", "label": "Stopped Prilosec left gastric mucosa unprotected when Advil was self-escalated to 2,400 mg/day"},
                {"from": "C2_2", "to": "C3_3", "label": "3 weeks of high-dose Advil caused acute upper GI bleed (Hgb 14.6 → 8.4 g/dL, BUN 46)"},
            ],
        },
    },

    # =========================================================================
    # pat-004: Evelyn Grace Carter (Austin, TX 78701)
    # =========================================================================
    {
        "patient_id": "pat-004",
        "given": ["Evelyn", "Grace"],
        "family": "Carter",
        "gender": "female",
        "birth_date": "1956-11-08",
        "phone": "512-555-0164",
        "pcp": "Dr. Robert Hayes, MD",
        "street": "901 Congress Ave",
        "city": "Austin",
        "state": "Texas",
        "postal_code": "78701",
        "lat": 30.2711,
        "lon": -97.7437,
        "todays_triage": {
            "encounter_id": "enc-pat004-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward Acute Triage",
            "chief_complaint": "Spontaneous epistaxis (nosebleed) x45 minutes, forearm ecchymoses, and palpitations.",
            "vitals": {
                "bp": "136/82 mmHg",
                "hr": "112 bpm (irregularly irregular)",
                "rr": "18 /min",
                "spo2": "98% on room air",
                "temp": "98.5 F",
                "weight_lbs": 146.0,
                "bmi": 24.3,
            },
            "ma_intake_note": (
                "70F on Coumadin for AFib arrived with persistent anterior epistaxis and large forearm bruises. "
                "Missed last 2 Anticoagulation Clinic INR checks and started OTC herbal cranberry/garlic supplements."
            ),
        },
        "allergies": [],
        "conditions": [
            {
                "id": "cond-tx-active-afib",
                "status": "active",
                "snomed": "49436004",
                "icd10": "I48.20",
                "display": "Chronic atrial fibrillation",
                "onset": "2020-02-18T10:00:00+00:00",
            }
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat004-anticoag",
                "doc_id": "doc-pat004-anticoag",
                "class_code": "AMB",
                "date": "2026-09-10",
                "type": "Anticoagulation Clinic Note",
                "facility": "Austin Heart & Vascular",
                "author": "Dr. Robert Hayes, MD",
                "primary_diagnosis": "AFib on Warfarin (Target INR 2.0 - 3.0)",
                "summary_note": "INR therapeutic at 2.4 on Coumadin 5mg daily. Next INR due 2026-10-08 (patient missed x2).",
            }
        ],
        "medications": [
            {
                "id": "med-tx-active-coumadin",
                "status": "active",
                "rxcui": "202421",
                "coding_display": "Coumadin",
                "text": "Coumadin 5 MG Oral Tablet",
                "authored_on": "2024-06-01T08:00:00+00:00",
                "dosage": "5 mg PO once daily; target INR 2.0-3.0",
                "prior_dose": "5 mg PO daily",
                "change_type": "SUPRATHERAPEUTIC INR 6.4 — HOLD COUMADIN STAT",
                "adherence": "Missed 2 monthly INR checks; taking OTC cranberry concentrate (CYP2C9 interaction).",
                "prescriber": "Dr. Robert Hayes, MD",
            },
            {
                "id": "med-tx-prev-aspirin",
                "status": "stopped",
                "rxcui": "1191",
                "coding_display": "Aspirin",
                "text": "Aspirin 81 MG Delayed Release Oral Tablet",
                "authored_on": "2019-05-10T08:00:00+00:00",
                "dosage": "Stopped upon initiation of warfarin therapy",
                "prior_dose": "81 mg PO daily",
                "reason": "Stopped to reduce dual antithrombotic bleeding risk.",
                "reinitiation_criteria": "Keep discontinued.",
                "prescriber": "Dr. Robert Hayes, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat004-inr",
                "loinc": "6301-6",
                "test": "INR (Prothrombin Time Ratio)",
                "unit": "ratio",
                "ref_range": "2.0 - 3.0 (Therapeutic AFib)",
                "history": [
                    {"date": "2026-08-12", "value": 2.3, "flag": "N", "context": "Anticoag Clinic"},
                    {"date": "2026-09-10", "value": 2.4, "flag": "N", "context": "Anticoag Clinic"},
                    {"date": "2026-11-12", "value": 6.4, "flag": "HH (Critical)", "context": "ED STAT Coags (Active Epistaxis)"},
                ],
            }
        ],
        "imaging": [],
        "open_loops": [
            {
                "id": "flag-pat004-1",
                "item_id": "OPEN-031",
                "priority": "CRITICAL",
                "category": "Supratherapeutic Warfarin Coagulopathy (INR 6.4) with Active Bleeding",
                "details": "Hold Coumadin immediately, administer oral/IV Vitamin K + nasal tamponade, and evaluate transitioning from Coumadin to a DOAC (Apixaban) given missed INR monitoring visits.",
            }
        ],
        "swimlane_headline": "Supratherapeutic Coumadin Toxicity (INR 6.4) & Active Epistaxis Following Missed INR Monitoring",
        "swimlane": {
            "age_sex": "70yo Female",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2026-09-10",
                    "display_date": "Sep 10, 2026",
                    "phase": "Therapeutic Baseline",
                    "tracks": {
                        "track_1_encounters": {"node_id": "D1_1", "title": "Anticoagulation Clinic", "badge": "THERAPEUTIC", "severity": "normal", "summary": "AFib stable; next INR scheduled 10/08.", "details": "Austin Heart & Vascular."},
                        "track_2_medications": {"node_id": "D1_2", "title": "Coumadin 5mg QD", "badge": "STABLE", "severity": "normal", "summary": "Maintaining target INR 2.0-3.0.", "details": "Aspirin previously stopped."},
                        "track_3_diagnostics": {"node_id": "D1_3", "title": "INR 2.4 [Therapeutic]", "badge": "IN RANGE", "severity": "normal", "summary": "Stable from Aug INR 2.3.", "details": "No bruising or bleeding."},
                        "track_4_open_loops": {"node_id": "D1_4", "title": "Monthly INR Required", "badge": "TRACKER", "severity": "info", "summary": "Narrow therapeutic index.", "details": "Due Oct 2026."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-10-08",
                    "display_date": "Oct 08 – Nov 05, 2026",
                    "phase": "Monitoring Gap",
                    "tracks": {
                        "track_1_encounters": {"node_id": "D2_1", "title": "Missed 2 INR Clinic Visits", "badge": "NO-SHOW", "severity": "warning", "summary": "8 weeks without INR surveillance.", "details": "Unmonitored anticoagulation."},
                        "track_2_medications": {"node_id": "D2_2", "title": "Coumadin + Herbal Supplements", "badge": "CYP2C9 INT", "severity": "warning", "summary": "Started OTC cranberry/garlic concentrates.", "details": "Potentiates warfarin anticoagulation."},
                        "track_3_diagnostics": {"node_id": "D2_3", "title": "Unmonitored Rising INR", "badge": "BLIND SPOT", "severity": "warning", "summary": "Forearm bruising developed 3 days ago.", "details": "No lab drawn until ED."},
                        "track_4_open_loops": {"node_id": "D2_4", "title": "Overdue Anticoag Recall", "badge": "HIGH", "severity": "warning", "summary": "Missed recall outreach.", "details": "Candidate for DOAC switch."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (ED Today)",
                    "phase": "ED Epistaxis",
                    "tracks": {
                        "track_1_encounters": {"node_id": "D3_1", "title": "ED Triage: Epistaxis & AFib HR 112", "badge": "ED BLEED", "severity": "critical", "summary": "45-min nosebleed & ecchymoses (ZIP 78701).", "details": "Direct nasal compression & packing."},
                        "track_2_medications": {"node_id": "D3_2", "title": "HOLD Coumadin + Give Vitamin K", "badge": "REVERSAL", "severity": "critical", "summary": "Hold Coumadin, stop supplements, plan DOAC switch.", "details": "Low-dose phytonadione administered."},
                        "track_3_diagnostics": {"node_id": "D3_3", "title": "STAT INR 6.4 [HH Critical]", "badge": "CRITICAL", "severity": "critical", "summary": "Markedly supratherapeutic INR 6.4.", "details": "Repeat INR in 12-24h."},
                        "track_4_open_loops": {"node_id": "D3_4", "title": "OPEN-031 DOAC Transition", "badge": "CRITICAL", "severity": "critical", "summary": "Transition to Apixaban once INR < 2.0.", "details": "Eliminates monthly INR monitoring gap."},
                    },
                },
            ],
            "causal_links": [
                {"from": "D2_1", "to": "D3_3", "label": "8-week missed INR gap + OTC CYP2C9 supplements allowed INR to climb to 6.4"},
                {"from": "D3_3", "to": "D3_1", "label": "Supratherapeutic INR 6.4 caused persistent epistaxis and ecchymoses"},
            ],
        },
    },

    # =========================================================================
    # pat-005 (MedicalChartAgent PAT-1001): Arthur Pendelton (Chicago, IL 60611)
    # =========================================================================
    {
        "patient_id": "pat-005",
        "legacy_id": "PAT-1001",
        "given": ["Arthur"],
        "family": "Pendelton",
        "gender": "male",
        "birth_date": "1958-03-14",
        "phone": "312-555-0181",
        "pcp": "Dr. Sarah Chen, MD",
        "street": "251 E Huron St",
        "city": "Chicago",
        "state": "Illinois",
        "postal_code": "60611",
        "lat": 41.8946,
        "lon": -87.6213,
        "todays_triage": {
            "encounter_id": "enc-pat005-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward / Post-Hospitalization Decompensation",
            "chief_complaint": "Increasing shortness of breath on exertion and bilateral ankle swelling over the past 5 days.",
            "vitals": {
                "bp": "148/90 mmHg",
                "hr": "88 bpm (irregularly irregular)",
                "rr": "20 /min",
                "spo2": "93% on room air",
                "temp": "98.4 F",
                "weight_lbs": 191.5,
                "bmi": 29.8,
            },
            "ma_intake_note": (
                "Patient states he feels winded walking from the parking lot. 2+ pitting edema noted up to mid-shins "
                "bilaterally (+7.5 lbs since 10/14 hospital discharge). Brought pill bottles; admits he reduced his "
                "water pill (Lasix) back to 20mg daily last week due to urinary frequency, and never picked up "
                "Jardiance because the pharmacy quoted $180 (Prior Authorization required)."
            ),
        },
        "allergies": [
            {
                "id": "allergy-il-penicillin",
                "substance": "Penicillin",
                "reaction": "Anaphylaxis (hives, airway swelling)",
                "criticality": "high",
                "severity": "severe",
            },
            {
                "id": "allergy-il-contrast",
                "substance": "Iodinated Contrast Dye",
                "reaction": "Mild urticaria",
                "criticality": "low",
                "severity": "moderate",
            },
        ],
        "conditions": [
            {"id": "cond-il-hfref", "status": "active", "snomed": "96675007", "icd10": "I50.22", "display": "Chronic systolic heart failure (HFrEF, EF 35%)", "onset": "2022-06-01T08:00:00+00:00"},
            {"id": "cond-il-ckd3b", "status": "active", "snomed": "709044004", "icd10": "N18.32", "display": "Chronic kidney disease, stage 3b (baseline Cr ~1.4 mg/dL)", "onset": "2023-01-15T08:00:00+00:00"},
            {"id": "cond-il-t2dm", "status": "active", "snomed": "44054006", "icd10": "E11.22", "display": "Type 2 diabetes mellitus with diabetic CKD", "onset": "2018-09-10T08:00:00+00:00"},
            {"id": "cond-il-afib", "status": "active", "snomed": "49436004", "icd10": "I48.91", "display": "Paroxysmal atrial fibrillation", "onset": "2023-11-05T08:00:00+00:00"},
            {"id": "cond-il-htn", "status": "active", "snomed": "59621000", "icd10": "I10", "display": "Essential hypertension", "onset": "2015-04-20T08:00:00+00:00"},
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat005-adhf",
                "doc_id": "doc-pat005-adhf",
                "class_code": "IMP",
                "date": "2026-10-10",
                "type": "Inpatient Hospitalization (Discharge Summary 10/10-10/14)",
                "facility": "Mercy General Hospital",
                "author": "Dr. Kevin Patel, MD (Hospitalist)",
                "primary_diagnosis": "Acute on Chronic Systolic Heart Failure Exacerbation (ADHF); Cardiorenal AKI on Stage 3b CKD",
                "summary_note": (
                    "68M with HFrEF (EF 35%), AFib on Eliquis, T2DM, and Stage 3b CKD admitted 10/10/2026 with dyspnea, "
                    "orthopnea, and 12-lb weight gain (196 lbs). Admission NT-proBNP 4,420 pg/mL; Cr 2.30 mg/dL (baseline 1.4). "
                    "Diuresed -5.5L with IV Furosemide; discharge weight 184.0 lbs, Cr 1.75 mg/dL. "
                    "Lisinopril 20mg and Metformin 1000mg BID HELD due to AKI. Started Jardiance 10mg daily; discharged on "
                    "Lasix 40mg BID x7d then 40mg daily. Incidental Finding on Admission CT Chest (10/10/2026): 7mm solid "
                    "non-calcified RUL lung nodule — needs 6-month follow-up CT Chest (April 2027) per Fleischner guidelines."
                ),
            },
            {
                "id": "enc-pat005-cards",
                "doc_id": "doc-pat005-cards",
                "class_code": "IMP",
                "date": "2026-10-13",
                "type": "Inpatient Cardiology Consult Note",
                "facility": "Mercy General Hospital",
                "author": "Dr. Elena Vance, MD (Cardiology)",
                "primary_diagnosis": "HFrEF Optimization & GDMT Plan",
                "summary_note": (
                    "TTE (10/12/2026) LVEF 30-35%, moderate MR. Keep Lisinopril HELD until outpatient Cr < 1.6 mg/dL and "
                    "K+ < 5.0; once Cr < 1.6, transition to Sacubitril/Valsartan (Entresto) 24/26mg BID (36h ACEi washout) "
                    "or restart ACEi. Continue Coreg 25mg BID and Eliquis 5mg BID. Start Jardiance 10mg daily."
                ),
            },
            {
                "id": "enc-pat005-pulm",
                "doc_id": "doc-pat005-pulm",
                "class_code": "AMB",
                "date": "2024-08-12",
                "type": "Outpatient Pulmonology Note",
                "facility": "Valley Pulmonary Associates",
                "author": "Dr. Marcus Reed, MD",
                "primary_diagnosis": "Former 35-pack-year smoker (quit 2019)",
                "summary_note": "PFTs: FEV1/FVC 0.68, FEV1 78% predicted (mild obstruction). High-risk former smoker.",
            },
        ],
        "medications": [
            {
                "id": "med-il-active-lasix",
                "status": "active",
                "rxcui": "202991",
                "coding_display": "Lasix",
                "text": "Lasix 40 MG Oral Tablet",
                "authored_on": "2026-10-14T10:00:00+00:00",
                "dosage": "40 mg PO BID x7 days, then 40 mg PO daily",
                "prior_dose": "20 mg PO daily (prior to 10/10 admission)",
                "change_type": "DOSE INCREASED at hospital discharge (10/14/2026)",
                "adherence": "NON-ADHERENT: Patient self-reduced back to 20 mg PO daily on 10/26/2026 due to urinary frequency.",
                "prescriber": "Dr. Kevin Patel, MD",
            },
            {
                "id": "med-il-active-jardiance",
                "status": "active",
                "rxcui": "1545658",
                "coding_display": "Jardiance",
                "text": "Jardiance 10 MG Oral Tablet",
                "authored_on": "2026-10-14T10:05:00+00:00",
                "dosage": "10 mg PO once daily",
                "prior_dose": "None",
                "change_type": "NEW START at hospital discharge (10/14/2026) for HFrEF/T2DM/CKD",
                "adherence": "NEVER STARTED: Pharmacy claim rejected 10/15/2026 ($180 Prior Authorization block).",
                "prescriber": "Dr. Kevin Patel, MD",
            },
            {
                "id": "med-il-active-coreg",
                "status": "active",
                "rxcui": "200033",
                "coding_display": "Coreg",
                "text": "Coreg 25 MG Oral Tablet",
                "authored_on": "2026-05-19T09:00:00+00:00",
                "dosage": "25 mg PO BID",
                "prior_dose": "25 mg PO BID",
                "change_type": "UNCHANGED",
                "adherence": "Adherent (refill picked up 10/02/2026).",
                "prescriber": "Dr. Sarah Chen, MD",
            },
            {
                "id": "med-il-active-eliquis",
                "status": "active",
                "rxcui": "1364435",
                "coding_display": "Eliquis",
                "text": "Eliquis 5 MG Oral Tablet",
                "authored_on": "2026-05-19T09:05:00+00:00",
                "dosage": "5 mg PO BID",
                "prior_dose": "5 mg PO BID",
                "change_type": "UNCHANGED",
                "adherence": "Adherent.",
                "prescriber": "Dr. Sarah Chen, MD",
            },
            {
                "id": "med-il-held-lisinopril",
                "status": "on-hold",
                "rxcui": "314077",
                "coding_display": "Lisinopril 20 MG Oral Tablet",
                "text": "Lisinopril 20 MG Oral Tablet",
                "authored_on": "2026-10-10T12:00:00+00:00",
                "dosage": "HELD during 10/10 hospital admission",
                "prior_dose": "20 mg PO daily",
                "reason": "Held for Acute Kidney Injury (Cr peaked at 2.30 mg/dL).",
                "reinitiation_criteria": "Cardiology criteria MET (Cr 1.50 < 1.6, K+ 4.2 < 5.0): Restart ACEi or switch to Entresto 24/26mg BID.",
                "prescriber": "Dr. Elena Vance, MD",
            },
            {
                "id": "med-il-held-metformin",
                "status": "on-hold",
                "rxcui": "861004",
                "coding_display": "Metformin hydrochloride 1000 MG Oral Tablet",
                "text": "Metformin hydrochloride 1000 MG Oral Tablet",
                "authored_on": "2026-10-10T12:05:00+00:00",
                "dosage": "HELD during 10/10 hospital admission",
                "prior_dose": "1000 mg PO BID",
                "reason": "Held due to acute renal dysfunction (eGFR dropped to 29 mL/min).",
                "reinitiation_criteria": "Safe to resume now that eGFR recovered to 48 mL/min (> 45 threshold).",
                "prescriber": "Dr. Kevin Patel, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat005-cr",
                "loinc": "2160-0",
                "test": "Serum Creatinine (mg/dL)",
                "unit": "mg/dL",
                "ref_range": "0.7 - 1.3",
                "history": [
                    {"date": "2026-05-19", "value": 1.40, "flag": "H", "context": "Outpatient Baseline"},
                    {"date": "2026-10-10", "value": 2.30, "flag": "HH (Critical)", "context": "Hospital Admission (AKI)"},
                    {"date": "2026-10-14", "value": 1.75, "flag": "H", "context": "Hospital Discharge"},
                    {"date": "2026-11-10", "value": 1.50, "flag": "H", "context": "Pre-Visit Lab (Recovered < 1.6!)"},
                ],
            },
            {
                "id_prefix": "lab-pat005-egfr",
                "loinc": "48642-3",
                "test": "eGFR (mL/min/1.73m2)",
                "unit": "mL/min/1.73m2",
                "ref_range": "> 60",
                "history": [
                    {"date": "2026-05-19", "value": 52, "flag": "L", "context": "Outpatient Baseline"},
                    {"date": "2026-10-10", "value": 29, "flag": "LL", "context": "Hospital Admission"},
                    {"date": "2026-10-14", "value": 40, "flag": "L", "context": "Hospital Discharge"},
                    {"date": "2026-11-10", "value": 48, "flag": "L", "context": "Pre-Visit Lab (Recovered > 45!)"},
                ],
            },
            {
                "id_prefix": "lab-pat005-bnp",
                "loinc": "33762-6",
                "test": "NT-proBNP (pg/mL)",
                "unit": "pg/mL",
                "ref_range": "< 125",
                "history": [
                    {"date": "2026-05-19", "value": 640, "flag": "H", "context": "Outpatient Baseline"},
                    {"date": "2026-10-10", "value": 4420, "flag": "HH", "context": "Hospital Admission"},
                    {"date": "2026-10-14", "value": 920, "flag": "H", "context": "Hospital Discharge"},
                    {"date": "2026-11-10", "value": 1850, "flag": "HH", "context": "Re-elevated (+7.5 lb fluid gain)"},
                ],
            },
            {
                "id_prefix": "lab-pat005-k",
                "loinc": "2823-3",
                "test": "Potassium (mEq/L)",
                "unit": "mEq/L",
                "ref_range": "3.5 - 5.1",
                "history": [
                    {"date": "2026-05-19", "value": 4.4, "flag": "N", "context": "Baseline"},
                    {"date": "2026-10-10", "value": 5.3, "flag": "H", "context": "Hospital Admission"},
                    {"date": "2026-11-10", "value": 4.2, "flag": "N", "context": "Recent Lab"},
                ],
            },
            {
                "id_prefix": "lab-pat005-a1c",
                "loinc": "4548-4",
                "test": "Hemoglobin A1c (%)",
                "unit": "%",
                "ref_range": "< 5.7",
                "history": [
                    {"date": "2026-05-19", "value": 7.1, "flag": "H", "context": "Outpatient"},
                    {"date": "2026-11-10", "value": 7.9, "flag": "H", "context": "Worsened while Metformin held & Jardiance blocked"},
                ],
            },
        ],
        "imaging": [
            {
                "id": "img-pat005-tte",
                "date": "2026-10-12",
                "category": "CUS",
                "modality": "Transthoracic Echocardiogram (TTE)",
                "findings": "LVEF 30-35%, global hypokinesis, moderate functional mitral regurgitation, RVSP 42 mmHg.",
            },
            {
                "id": "img-pat005-ct",
                "date": "2026-10-10",
                "category": "RAD",
                "modality": "CT Chest without Contrast",
                "findings": "Small bilateral pleural effusions and interstitial edema. INCIDENTAL FINDING: 7mm solid non-calcified RUL nodule in a 35-pack-year former smoker — recommend 6-month follow-up CT Chest (April 2027) per Fleischner guidelines.",
            },
        ],
        "open_loops": [
            {"id": "flag-pat005-1", "item_id": "OPEN-101", "priority": "CRITICAL", "category": "Early Volume Overload / Re-hospitalization Risk", "details": "Gained +7.5 lbs since discharge (184 -> 191.5 lbs), NT-proBNP doubled (920 -> 1,850 pg/mL), self-cut Lasix 40mg -> 20mg, and Jardiance blocked by $180 Prior Authorization."},
            {"id": "flag-pat005-2", "item_id": "OPEN-102", "priority": "HIGH", "category": "Held Medications Ready for Re-initiation (Renal Recovery)", "details": "Cr recovered to 1.50 mg/dL (eGFR 48) and K+ is 4.2. Meets Cardiology criteria (Cr < 1.6) to initiate Entresto (or restart Lisinopril) AND eGFR > 45 criteria to resume Metformin."},
            {"id": "flag-pat005-3", "item_id": "OPEN-103", "priority": "HIGH", "category": "Unordered Incidental 7mm RUL Lung Nodule Follow-Up", "details": "6-month follow-up CT Chest (due April 2027) for 7mm RUL nodule in 35-pack-year former smoker has NOT been ordered."},
            {"id": "flag-pat005-4", "item_id": "OPEN-104", "priority": "MEDIUM", "category": "Missed Heart Failure Clinic Appointment", "details": "No-showed to 2026-10-24 Heart Failure Clinic visit due to transportation barrier."},
        ],
        "swimlane_headline": "Post-ADHF Volume Overload (Lasix Self-Cut + Jardiance PA Block) & Renal Recovery Unlocking Held GDMT",
        "swimlane": {
            "age_sex": "68yo Male",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2026-05-19",
                    "display_date": "May 19, 2026",
                    "phase": "Euvolemic Baseline",
                    "tracks": {
                        "track_1_encounters": {"node_id": "N1_1", "title": "PCP Visit", "badge": "EUVOLEMIC", "severity": "normal", "summary": "Wt 183 lbs, BP 124/76; 35-pk-yr history.", "details": "Stable chronic HFrEF (EF 35%), CKD3b, T2DM."},
                        "track_2_medications": {"node_id": "N1_2", "title": "Baseline GDMT + Metformin", "badge": "ADHERENT", "severity": "normal", "summary": "Lasix 20mg, Lisinopril 20mg, Coreg, Metformin, Eliquis.", "details": "Stable outpatient regimen."},
                        "track_3_diagnostics": {"node_id": "N1_3", "title": "Cr 1.40 | BNP 640 | A1c 7.1%", "badge": "BASELINE", "severity": "normal", "summary": "eGFR 52 · K+ 4.4 · PFTs FEV1/FVC 0.68.", "details": "Outpatient baseline."},
                        "track_4_open_loops": {"node_id": "N1_4", "title": "High-Risk Lung History", "badge": "CONTEXT", "severity": "info", "summary": "35-pack-year smoking history.", "details": "Anchors Fleischner lung nodule criteria."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-10-10",
                    "display_date": "Oct 10–14, 2026",
                    "phase": "ADHF Admission & AKI",
                    "tracks": {
                        "track_1_encounters": {"node_id": "N2_1", "title": "ADHF Admission & Cards Consult", "badge": "INPATIENT", "severity": "critical", "summary": "Wt 196 → 184 lbs (-5.5L IV diuresis).", "details": "Cardiology set Cr < 1.6 threshold to start Entresto."},
                        "track_2_medications": {"node_id": "N2_2", "title": "HELD ACEi/Metformin; +Jardiance/Lasix↑", "badge": "REGIMEN CHG", "severity": "warning", "summary": "Lisinopril & Metformin HELD for AKI; Lasix 40mg + Jardiance.", "details": "Discharged 10/14."},
                        "track_3_diagnostics": {"node_id": "N2_3", "title": "Cr 2.30→1.75 | BNP 4,420 | 7mm Nodule", "badge": "CRITICAL", "severity": "critical", "summary": "TTE EF 30-35%; CT Chest incidental 7mm RUL nodule.", "details": "AKI improving at discharge."},
                        "track_4_open_loops": {"node_id": "N2_4", "title": "OPEN-103 Unordered 6-mo CT", "badge": "HIGH", "severity": "warning", "summary": "Fleischner Apr 2027 CT Chest never ordered.", "details": "HF clinic set for 10/24."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-10-24",
                    "display_date": "Oct 15–26, 2026",
                    "phase": "Post-Discharge Gaps",
                    "tracks": {
                        "track_1_encounters": {"node_id": "N3_1", "title": "NO-SHOW: HF Clinic (10/24)", "badge": "MISSED VISIT", "severity": "warning", "summary": "Missed HF follow-up (transportation).", "details": "OPEN-104 care transition gap."},
                        "track_2_medications": {"node_id": "N3_2", "title": "Jardiance PA Blocked + Lasix Cut", "badge": "NON-ADHERENT", "severity": "critical", "summary": "$180 PA blocked Jardiance; self-cut Lasix 40→20mg.", "details": "Cut loop diuretic in half due to urination."},
                        "track_3_diagnostics": {"node_id": "N3_3", "title": "+7.5 lb Fluid Re-accumulation", "badge": "UNMONITORED", "severity": "warning", "summary": "Progressive edema & dyspnea.", "details": "Weight rose 184 -> 191.5 lbs."},
                        "track_4_open_loops": {"node_id": "N3_4", "title": "Compounded Readmission Risk", "badge": "CRITICAL", "severity": "critical", "summary": "Under-diuresed + off SGLT2i + off RAASi.", "details": "Triggers OPEN-101."},
                    },
                },
                {
                    "time_id": "T4",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (Today)",
                    "phase": "Triage & Action Plan",
                    "tracks": {
                        "track_1_encounters": {"node_id": "N4_1", "title": "Triage: SpO2 93%, BP 148/90", "badge": "TODAY", "severity": "critical", "summary": "2+ shin edema, Wt 191.5 lbs (Chicago ZIP 60611).", "details": "Early ADHF decompensation."},
                        "track_2_medications": {"node_id": "N4_2", "title": "Restore Lasix 40mg + Start Entresto/Metformin", "badge": "UNLOCK GDMT", "severity": "warning", "summary": "Submit Jardiance PA; resume GDMT & Metformin.", "details": "36h washout already satisfied since ACEi held."},
                        "track_3_diagnostics": {"node_id": "N4_3", "title": "Cr 1.50 (eGFR 48) | BNP 1,850 | A1c 7.9%", "badge": "RENAL OK", "severity": "critical", "summary": "Renal recovery unlocks ACEi/ARNI & Metformin!", "details": "NT-proBNP doubled to 1,850."},
                        "track_4_open_loops": {"node_id": "N4_4", "title": "Close OPEN-101, 102, 103", "badge": "ACTION", "severity": "critical", "summary": "1. Diurese & PA 2. Start Entresto/Metformin 3. Order RUL CT.", "details": "Prevents inpatient readmission."},
                    },
                },
            ],
            "causal_links": [
                {"from": "N2_3", "to": "N2_2", "label": "Cardiorenal AKI (Cr 2.30) forced holding Lisinopril & Metformin"},
                {"from": "N3_2", "to": "N4_1", "label": "Self-cutting Lasix + $180 Jardiance PA block caused +7.5 lb fluid gain & BNP 1,850"},
                {"from": "N4_3", "to": "N4_2", "label": "Renal recovery (Cr 1.50, eGFR 48) unlocks Entresto/ACEi and Metformin restart today"},
            ],
        },
    },

    # =========================================================================
    # pat-006 (MedicalChartAgent PAT-1002): Elena Rostova (Seattle, WA 98104)
    # =========================================================================
    {
        "patient_id": "pat-006",
        "legacy_id": "PAT-1002",
        "given": ["Elena"],
        "family": "Rostova",
        "gender": "female",
        "birth_date": "1972-07-22",
        "phone": "206-555-0139",
        "pcp": "Dr. Sarah Chen, MD",
        "street": "325 9th Ave",
        "city": "Seattle",
        "state": "Washington",
        "postal_code": "98104",
        "lat": 47.6040,
        "lon": -122.3242,
        "todays_triage": {
            "encounter_id": "enc-pat006-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward / Acute Drug Toxicity Triage",
            "chief_complaint": "Persistent severe fatigue, nausea, RUQ discomfort, morning hand stiffness, and abnormal labs.",
            "vitals": {
                "bp": "118/74 mmHg",
                "hr": "76 bpm",
                "rr": "14 /min",
                "spo2": "99% on room air",
                "temp": "98.1 F",
                "weight_lbs": 142.0,
                "bmi": 23.6,
            },
            "ma_intake_note": (
                "Patient reports exhaustion and nausea for 2 weeks after increasing weekly Methotrexate from 15mg to "
                "20mg. Also takes morning Synthroid at 7 AM simultaneously with oral Ferrous Sulfate started after her "
                "9/18 ED gastritis visit."
            ),
        },
        "allergies": [
            {
                "id": "allergy-wa-sulfa",
                "substance": "Sulfa Antibiotics (TMP-SMX)",
                "reaction": "Maculopapular rash",
                "criticality": "high",
                "severity": "moderate",
            }
        ],
        "conditions": [
            {"id": "cond-wa-ra", "status": "active", "snomed": "69896004", "icd10": "M05.79", "display": "Seropositive rheumatoid arthritis", "onset": "2021-03-12T08:00:00+00:00"},
            {"id": "cond-wa-hypo", "status": "active", "snomed": "40930008", "icd10": "E03.9", "display": "Hypothyroidism", "onset": "2019-11-04T08:00:00+00:00"},
            {"id": "cond-wa-gastritis", "status": "active", "snomed": "4556007", "icd10": "K29.70", "display": "NSAID-induced gastritis", "onset": "2026-09-18T08:00:00+00:00"},
            {"id": "cond-wa-ida", "status": "active", "snomed": "87522002", "icd10": "D50.9", "display": "Iron deficiency anemia", "onset": "2026-09-18T08:00:00+00:00"},
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat006-rheum",
                "doc_id": "doc-pat006-rheum",
                "class_code": "AMB",
                "date": "2026-10-05",
                "type": "Outpatient Rheumatology Consult Note",
                "facility": "Metro Rheumatology",
                "author": "Dr. Priya Nair, MD (Rheumatology)",
                "primary_diagnosis": "Active Seropositive Rheumatoid Arthritis Flare",
                "summary_note": (
                    "Active MCP/PIP synovitis after stopping NSAIDs. Increased Methotrexate 15mg -> 20mg PO weekly + "
                    "Folic Acid 1mg daily; prescribed 21-day Prednisone taper (completed 10/26). Planned Humira 40mg SC "
                    "q2w pending negative QuantiFERON-TB Gold and Hepatitis B/C screening."
                ),
            },
            {
                "id": "enc-pat006-ed",
                "doc_id": "doc-pat006-ed",
                "class_code": "EMER",
                "date": "2026-09-18",
                "type": "Emergency Department Visit Note",
                "facility": "Mercy General Hospital ED",
                "author": "Dr. Thomas Wright, MD (Emergency Medicine)",
                "primary_diagnosis": "Acute NSAID-Induced Gastritis; Microcytic Anemia",
                "summary_note": (
                    "Presented with epigastric pain and dark stools after OTC Ibuprofen 600mg TID x3w. Hgb 9.8 g/dL, "
                    "Ferritin 12 ng/mL. Discharged on Protonix 40mg daily and Ferrous Sulfate 325mg QOD; strictly avoid "
                    "NSAIDs. Recommended outpatient GI EGD referral and H. pylori testing."
                ),
            },
        ],
        "medications": [
            {
                "id": "med-wa-active-mtx",
                "status": "active",
                "rxcui": "105585",
                "coding_display": "Methotrexate 2.5 MG Oral Tablet",
                "text": "Methotrexate 2.5 MG Oral Tablet (20 mg weekly)",
                "authored_on": "2026-10-05T10:00:00+00:00",
                "dosage": "20 mg (8 tablets) PO once weekly",
                "prior_dose": "15 mg PO once weekly",
                "change_type": "DOSE INCREASED on 2026-10-05 -> ACUTE HEPATOTOXICITY",
                "adherence": "Adherent; experiencing nausea and ALT/AST spike to 92/78 U/L (>2.5x ULN).",
                "prescriber": "Dr. Priya Nair, MD",
            },
            {
                "id": "med-wa-active-synthroid",
                "status": "active",
                "rxcui": "966247",
                "coding_display": "Synthroid",
                "text": "Synthroid 75 MCG Oral Tablet",
                "authored_on": "2025-04-10T09:00:00+00:00",
                "dosage": "75 mcg PO every morning",
                "prior_dose": "75 mcg PO daily",
                "change_type": "ABSORPTION INTERACTION w/ morning Ferrous Sulfate",
                "adherence": "Takes at 7 AM simultaneously with Ferrous Sulfate -> chelates thyroxine (TSH spiked 2.4 -> 6.8).",
                "prescriber": "Dr. Sarah Chen, MD",
            },
            {
                "id": "med-wa-active-iron",
                "status": "active",
                "rxcui": "310325",
                "coding_display": "Ferrous sulfate 325 MG Oral Tablet",
                "text": "Ferrous sulfate 325 MG Oral Tablet",
                "authored_on": "2026-09-18T16:00:00+00:00",
                "dosage": "325 mg PO every other day",
                "prior_dose": "None",
                "change_type": "NEW START at 9/18 ED discharge",
                "adherence": "Taking at 7 AM with Synthroid; separate by >= 4 hours.",
                "prescriber": "Dr. Thomas Wright, MD",
            },
            {
                "id": "med-wa-active-protonix",
                "status": "active",
                "rxcui": "261106",
                "coding_display": "Protonix",
                "text": "Protonix 40 MG Delayed Release Oral Tablet",
                "authored_on": "2026-09-18T16:05:00+00:00",
                "dosage": "40 mg PO once daily",
                "prior_dose": "None",
                "change_type": "NEW START at 9/18 ED discharge",
                "adherence": "Adherent; epigastric pain improved.",
                "prescriber": "Dr. Thomas Wright, MD",
            },
            {
                "id": "med-wa-stopped-ibuprofen",
                "status": "stopped",
                "rxcui": "197806",
                "coding_display": "Ibuprofen 600 MG Oral Tablet",
                "text": "Ibuprofen 600 MG Oral Tablet",
                "authored_on": "2026-09-18T16:10:00+00:00",
                "dosage": "DISCONTINUED permanently on 2026-09-18",
                "prior_dose": "600 mg PO TID",
                "reason": "NSAID-induced gastritis and GI blood loss anemia.",
                "reinitiation_criteria": "Contraindicated.",
                "prescriber": "Dr. Thomas Wright, MD",
            },
            {
                "id": "med-wa-completed-prednisone",
                "status": "completed",
                "rxcui": "312617",
                "coding_display": "Prednisone 5 MG Oral Tablet",
                "text": "Prednisone 5 MG Oral Tablet (21-day taper)",
                "authored_on": "2026-10-05T10:10:00+00:00",
                "dosage": "15 mg taper over 21 days (completed 10/26/2026)",
                "prior_dose": "15 mg taper",
                "reason": "Bridge therapy for RA flare (caused indeterminate QuantiFERON on 10/12).",
                "reinitiation_criteria": "Now off steroids >2 weeks — safe to repeat QuantiFERON-TB Gold.",
                "prescriber": "Dr. Priya Nair, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat006-alt",
                "loinc": "1742-6",
                "test": "ALT (U/L)",
                "unit": "U/L",
                "ref_range": "7 - 35",
                "history": [
                    {"date": "2026-04-10", "value": 19, "flag": "N", "context": "Baseline on MTX 15mg"},
                    {"date": "2026-09-18", "value": 24, "flag": "N", "context": "ED Visit"},
                    {"date": "2026-11-08", "value": 92, "flag": "HH (>2.5x ULN)", "context": "After MTX increase to 20mg/wk"},
                ],
            },
            {
                "id_prefix": "lab-pat006-ast",
                "loinc": "1920-8",
                "test": "AST (U/L)",
                "unit": "U/L",
                "ref_range": "8 - 33",
                "history": [
                    {"date": "2026-04-10", "value": 22, "flag": "N", "context": "Baseline on MTX 15mg"},
                    {"date": "2026-09-18", "value": 25, "flag": "N", "context": "ED Visit"},
                    {"date": "2026-11-08", "value": 78, "flag": "HH (>2x ULN)", "context": "After MTX increase to 20mg/wk"},
                ],
            },
            {
                "id_prefix": "lab-pat006-tsh",
                "loinc": "3016-3",
                "test": "TSH (mIU/L)",
                "unit": "mIU/L",
                "ref_range": "0.45 - 4.50",
                "history": [
                    {"date": "2026-04-10", "value": 2.4, "flag": "N", "context": "Euthyroid Baseline"},
                    {"date": "2026-11-08", "value": 6.8, "flag": "H", "context": "Elevated due to Iron + Synthroid co-administration"},
                ],
            },
            {
                "id_prefix": "lab-pat006-hgb",
                "loinc": "718-7",
                "test": "Hemoglobin (g/dL)",
                "unit": "g/dL",
                "ref_range": "12.0 - 16.0",
                "history": [
                    {"date": "2026-04-10", "value": 12.4, "flag": "N", "context": "Outpatient"},
                    {"date": "2026-09-18", "value": 9.8, "flag": "L", "context": "ED Gastritis"},
                    {"date": "2026-11-08", "value": 10.9, "flag": "L", "context": "Improving on Iron + Protonix"},
                ],
            },
            {
                "id_prefix": "lab-pat006-qft",
                "loinc": "64084-7",
                "test": "QuantiFERON-TB Gold Plus",
                "unit": "qualitative",
                "ref_range": "Negative",
                "history": [
                    {"date": "2026-10-12", "value_str": "INDETERMINATE (Low Mitogen on Prednisone)", "flag": "ABNORMAL", "context": "Pre-Humira TB screen stalled"},
                ],
            },
        ],
        "imaging": [],
        "open_loops": [
            {"id": "flag-pat006-1", "item_id": "OPEN-201", "priority": "CRITICAL", "category": "Drug-Induced Hepatotoxicity (Methotrexate 20mg/wk)", "details": "ALT 92 / AST 78 U/L with nausea after MTX increase. Hold/reduce MTX, increase Folic Acid, and coordinate with Rheumatology."},
            {"id": "flag-pat006-2", "item_id": "OPEN-202", "priority": "HIGH", "category": "Synthroid + Ferrous Sulfate Malabsorption Interaction", "details": "TSH jumped 2.4 -> 6.8 mIU/L because morning Iron chelates Synthroid. Separate Iron by >= 4 hours before altering Synthroid dose."},
            {"id": "flag-pat006-3", "item_id": "OPEN-203", "priority": "HIGH", "category": "Stalled Pre-Humira TB Screening", "details": "10/12 QuantiFERON-TB was Indeterminate while on Prednisone (completed 10/26). Repeat TB test + CXR to unlock Adalimumab."},
            {"id": "flag-pat006-4", "item_id": "OPEN-204", "priority": "MEDIUM", "category": "Unplaced GI / EGD Referral from 9/18 ED Visit", "details": "ED recommended outpatient Gastroenterology EGD for iron-deficiency anemia; referral still not placed."},
        ],
        "swimlane_headline": "Methotrexate Hepatotoxicity (ALT 92/AST 78), Iron-Synthroid Malabsorption (TSH 6.8) & Stalled Humira Start",
        "swimlane": {
            "age_sex": "54yo Female",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2026-04-10",
                    "display_date": "Apr 10, 2026",
                    "phase": "Baseline",
                    "tracks": {
                        "track_1_encounters": {"node_id": "E1_1", "title": "Routine Outpatient Care", "badge": "STABLE", "severity": "normal", "summary": "RA & Hypothyroidism controlled.", "details": "Baseline labs normal."},
                        "track_2_medications": {"node_id": "E1_2", "title": "MTX 15mg/wk + Synthroid 75mcg", "badge": "TOLERATED", "severity": "normal", "summary": "Stable on MTX 15mg & morning Synthroid.", "details": "No iron supplement yet."},
                        "track_3_diagnostics": {"node_id": "E1_3", "title": "ALT 19 | TSH 2.4 | Hgb 12.4", "badge": "NORMAL", "severity": "normal", "summary": "Normal LFTs, euthyroid, normal Hgb.", "details": "AST 22 U/L."},
                        "track_4_open_loops": {"node_id": "E1_4", "title": "Sulfa Allergy Documented", "badge": "ALLERGY", "severity": "info", "summary": "Moderate rash to TMP-SMX.", "details": "Active allergy flag."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-09-18",
                    "display_date": "Sep 18, 2026",
                    "phase": "ED NSAID Gastritis",
                    "tracks": {
                        "track_1_encounters": {"node_id": "E2_1", "title": "ED Visit: Gastritis & Anemia", "badge": "ED VISIT", "severity": "critical", "summary": "Epigastric pain after OTC Ibuprofen.", "details": "Advised GI EGD referral."},
                        "track_2_medications": {"node_id": "E2_2", "title": "STOP Ibuprofen; +Iron & Protonix", "badge": "NEW IRON", "severity": "warning", "summary": "Started morning Ferrous Sulfate WITH Synthroid!", "details": "Unrecognized chelation interaction."},
                        "track_3_diagnostics": {"node_id": "E2_3", "title": "Hgb 9.8 [L] | Ferritin 12 | ALT 24", "badge": "ANEMIA", "severity": "warning", "summary": "Microcytic blood-loss anemia; LFTs normal.", "details": "Hemoccult borderline (+)."},
                        "track_4_open_loops": {"node_id": "E2_4", "title": "OPEN-204 GI EGD Not Ordered", "badge": "MEDIUM", "severity": "warning", "summary": "Outpatient EGD referral dropped.", "details": "Needs GI order."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-10-05",
                    "display_date": "Oct 05–12, 2026",
                    "phase": "Rheum Flare & TB Screen",
                    "tracks": {
                        "track_1_encounters": {"node_id": "E3_1", "title": "Rheumatology Consult", "badge": "FLARE", "severity": "info", "summary": "RA flare off NSAIDs; planned Humira.", "details": "Dr. P. Nair."},
                        "track_2_medications": {"node_id": "E3_2", "title": "MTX ↑20mg/wk + Prednisone Taper", "badge": "DOSE UP", "severity": "warning", "summary": "MTX increased; 21d steroid taper (ended 10/26).", "details": "Humira held pending TB test."},
                        "track_3_diagnostics": {"node_id": "E3_3", "title": "QuantiFERON: INDETERMINATE", "badge": "ABNORMAL", "severity": "warning", "summary": "Low mitogen response due to Prednisone.", "details": "Drawn 10/12 on steroids."},
                        "track_4_open_loops": {"node_id": "E3_4", "title": "OPEN-203 Humira Stalled", "badge": "HIGH", "severity": "warning", "summary": "Repeat TB test needed now off steroids.", "details": "Blocks biologic start."},
                    },
                },
                {
                    "time_id": "T4",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (Today)",
                    "phase": "Toxicity & Malabsorption",
                    "tracks": {
                        "track_1_encounters": {"node_id": "E4_1", "title": "Triage: Nausea & Exhaustion", "badge": "TODAY", "severity": "critical", "summary": "2w nausea & severe fatigue (Seattle ZIP 98104).", "details": "Vitals stable."},
                        "track_2_medications": {"node_id": "E4_2", "title": "Hold/Cut MTX; Separate Iron ≥4h", "badge": "ACTION", "severity": "critical", "summary": "Reduce/hold MTX + ↑Folic Acid; move Iron to dinner.", "details": "Do not increase Synthroid prematurely."},
                        "track_3_diagnostics": {"node_id": "E4_3", "title": "ALT 92 [HH] | AST 78 | TSH 6.8 [H]", "badge": "CRITICAL", "severity": "critical", "summary": "MTX transaminitis + Iron-chelated hypothyroidism.", "details": "Hgb improved to 10.9."},
                        "track_4_open_loops": {"node_id": "E4_4", "title": "Resolve OPEN-201..204", "badge": "CRITICAL", "severity": "critical", "summary": "1. Hold MTX 2. Separate Iron 3. Repeat QFT 4. GI EGD.", "details": "Full 4-loop closure."},
                    },
                },
            ],
            "causal_links": [
                {"from": "E2_2", "to": "E4_3", "label": "Morning Ferrous Sulfate chelated Synthroid absorption, spiking TSH 2.4 → 6.8 mIU/L"},
                {"from": "E3_2", "to": "E4_3", "label": "Methotrexate increase to 20mg/wk caused acute hepatotoxicity (ALT 92 / AST 78) & nausea"},
                {"from": "E3_2", "to": "E3_3", "label": "Prednisone taper caused indeterminate QuantiFERON-TB, stalling Humira"},
            ],
        },
    },

    # =========================================================================
    # pat-007 (MedicalChartAgent PAT-1003): Marcus Vance (Denver, CO 80203)
    # =========================================================================
    {
        "patient_id": "pat-007",
        "legacy_id": "PAT-1003",
        "given": ["Marcus"],
        "family": "Vance",
        "gender": "male",
        "birth_date": "1984-02-10",
        "phone": "303-555-0155",
        "pcp": "Dr. Sarah Chen, MD",
        "street": "777 Bannock St",
        "city": "Denver",
        "state": "Colorado",
        "postal_code": "80203",
        "lat": 39.7282,
        "lon": -104.9892,
        "todays_triage": {
            "encounter_id": "enc-pat007-triage",
            "visit_date": "2026-11-12",
            "appointment_type": "Emergency Ward / Post-ED Hypertensive & Electrolyte Alert",
            "chief_complaint": "Bilateral calf cramps, generalized muscle weakness, and elevated BP 168/102 after starting ER water pill.",
            "vitals": {
                "bp": "168/102 mmHg",
                "hr": "78 bpm",
                "rr": "16 /min",
                "spo2": "98% on room air",
                "temp": "98.6 F",
                "weight_lbs": 210.0,
                "bmi": 30.1,
            },
            "ma_intake_note": (
                "42M post-ER visit (BP 210/118 occipital headache 4 days ago); complains of painful bilateral calf "
                "cramps and muscle weakness for 2 days since starting Chlorthalidone 25mg prescribed in the ER."
            ),
        },
        "allergies": [],
        "conditions": [
            {"id": "cond-co-htn", "status": "active", "snomed": "59621000", "icd10": "I10", "display": "Resistant essential hypertension", "onset": "2023-05-10T08:00:00+00:00"},
            {"id": "cond-co-hypok", "status": "active", "snomed": "43339004", "icd10": "E87.6", "display": "Hypokalemia", "onset": "2025-11-10T08:00:00+00:00"},
            {"id": "cond-co-osa", "status": "active", "snomed": "78275009", "icd10": "G47.33", "display": "Obstructive sleep apnea", "onset": "2024-02-14T08:00:00+00:00"},
        ],
        "encounters_and_notes": [
            {
                "id": "enc-pat007-ed",
                "doc_id": "doc-pat007-ed",
                "class_code": "EMER",
                "date": "2026-11-08",
                "type": "Emergency Department Visit Note",
                "facility": "Mercy General Hospital ED",
                "author": "Dr. Hannah Kim, MD (Emergency Medicine)",
                "primary_diagnosis": "Hypertensive Urgency (BP 210/118); Hypokalemia (K+ 3.2)",
                "summary_note": (
                    "42M with occipital headache and BP 210/118 despite Lisinopril 40mg + Norvasc 5mg. CT Head negative. "
                    "ED Potassium 3.2 mEq/L (given single 40 mEq PO KCl dose). Discharged on Norvasc increased to 10mg, "
                    "Lisinopril 40mg, and ADDED Chlorthalidone 25mg PO daily without noticing chronic low K+ or August ARR."
                ),
            },
            {
                "id": "enc-pat007-pcp",
                "doc_id": "doc-pat007-pcp",
                "class_code": "AMB",
                "date": "2026-08-14",
                "type": "Outpatient Secondary Hypertension Workup Note",
                "facility": "Valley Internal Medicine",
                "author": "Dr. Sarah Chen, MD",
                "primary_diagnosis": "Secondary Hypertension Screening",
                "summary_note": "Persistent BP 165/104 and borderline low K+ (3.5) off diuretics. Ordered morning Aldosterone & Renin.",
            },
        ],
        "medications": [
            {
                "id": "med-co-active-chlorthalidone",
                "status": "active",
                "rxcui": "309114",
                "coding_display": "Chlorthalidone 25 MG Oral Tablet",
                "text": "Chlorthalidone 25 MG Oral Tablet",
                "authored_on": "2026-11-08T18:00:00+00:00",
                "dosage": "25 mg PO once daily",
                "prior_dose": "None",
                "change_type": "UNSAFE NEW START at ED discharge despite K+ 3.2 mEq/L!",
                "adherence": "Taken x4 days -> now has symptomatic calf cramps & weakness (acute severe hypokalemia risk!).",
                "prescriber": "Dr. Hannah Kim, MD",
            },
            {
                "id": "med-co-active-norvasc",
                "status": "active",
                "rxcui": "58927",
                "coding_display": "Norvasc",
                "text": "Norvasc 10 MG Oral Tablet",
                "authored_on": "2026-11-08T18:05:00+00:00",
                "dosage": "10 mg PO once daily",
                "prior_dose": "5 mg PO once daily",
                "change_type": "DOSE INCREASED at ED discharge (2026-11-08)",
                "adherence": "Adherent.",
                "prescriber": "Dr. Hannah Kim, MD",
            },
            {
                "id": "med-co-active-lisinopril",
                "status": "active",
                "rxcui": "314078",
                "coding_display": "Lisinopril 40 MG Oral Tablet",
                "text": "Lisinopril 40 MG Oral Tablet",
                "authored_on": "2025-11-10T09:00:00+00:00",
                "dosage": "40 mg PO once daily",
                "prior_dose": "40 mg PO once daily",
                "change_type": "UNCHANGED",
                "adherence": "Adherent.",
                "prescriber": "Dr. Sarah Chen, MD",
            },
        ],
        "labs": [
            {
                "id_prefix": "lab-pat007-k",
                "loinc": "2823-3",
                "test": "Potassium (mEq/L)",
                "unit": "mEq/L",
                "ref_range": "3.5 - 5.1",
                "history": [
                    {"date": "2025-11-10", "value": 3.4, "flag": "L", "context": "Outpatient (off diuretics)"},
                    {"date": "2026-08-14", "value": 3.5, "flag": "N (Borderline)", "context": "Secondary HTN Workup"},
                    {"date": "2026-11-08", "value": 3.2, "flag": "LL", "context": "ED Visit BEFORE Chlorthalidone start!"},
                ],
            },
            {
                "id_prefix": "lab-pat007-aldo",
                "loinc": "1763-2",
                "test": "Plasma Aldosterone Concentration (ng/dL)",
                "unit": "ng/dL",
                "ref_range": "4.0 - 21.0",
                "history": [
                    {"date": "2026-08-18", "value": 28.5, "flag": "HH", "context": "Send-out Lab (UNREVIEWED)"},
                ],
            },
            {
                "id_prefix": "lab-pat007-renin",
                "loinc": "2915-7",
                "test": "Plasma Renin Activity (ng/mL/hr)",
                "unit": "ng/mL/hr",
                "ref_range": "0.6 - 4.3",
                "history": [
                    {"date": "2026-08-18", "value": 0.3, "flag": "LL (Suppressed)", "context": "Send-out Lab (UNREVIEWED)"},
                ],
            },
            {
                "id_prefix": "lab-pat007-arr",
                "loinc": "30894-0",
                "test": "Aldosterone-to-Renin Ratio (ARR)",
                "unit": "ratio",
                "ref_range": "< 20",
                "history": [
                    {"date": "2026-08-18", "value": 95.0, "flag": "CRITICAL HIGH (>30 diagnostic)", "context": "Diagnostic for Primary Hyperaldosteronism (Conn's Syndrome)"},
                ],
            },
        ],
        "imaging": [
            {
                "id": "img-pat007-cthead",
                "date": "2026-11-08",
                "category": "RAD",
                "modality": "CT Head without Contrast",
                "findings": "No acute intracranial hemorrhage, mass effect, or territorial infarction.",
            }
        ],
        "open_loops": [
            {"id": "flag-pat007-1", "item_id": "OPEN-301", "priority": "CRITICAL", "category": "CRITICAL Drug-Lab Alert: Chlorthalidone Started on K+ 3.2 mEq/L", "details": "Patient has bilateral calf cramps & muscle weakness after 4 days of potassium-wasting Chlorthalidone. STOP Chlorthalidone immediately, draw STAT BMP/K+ & 12-lead ECG, and replete potassium."},
            {"id": "flag-pat007-2", "item_id": "OPEN-302", "priority": "CRITICAL", "category": "Unreviewed Send-Out Lab: ARR = 95 (Primary Hyperaldosteronism)", "details": "2026-08-18 Aldosterone 28.5 / Renin 0.3 (ARR 95) confirms Conn's Syndrome. Order Adrenal Protocol CT Abdomen, refer to Endocrinology, and initiate Spironolactone or Eplerenone."},
        ],
        "swimlane_headline": "Unsafe Chlorthalidone on K+ 3.2 mEq/L (Calf Cramps) & Unreviewed ARR=95 Confirming Conn's Syndrome",
        "swimlane": {
            "age_sex": "42yo Male",
            "timepoints": [
                {
                    "time_id": "T1",
                    "date": "2025-11-10",
                    "display_date": "Nov 10, 2025",
                    "phase": "Spontaneous Low K+",
                    "tracks": {
                        "track_1_encounters": {"node_id": "V1_1", "title": "Outpatient HTN Visit", "badge": "RESISTANT HTN", "severity": "info", "summary": "42yo w/ persistent HTN.", "details": "Off diuretics."},
                        "track_2_medications": {"node_id": "V1_2", "title": "Lisinopril 40mg + Norvasc 5mg", "badge": "DUAL TX", "severity": "normal", "summary": "Adherent on ACEi + CCB.", "details": "No diuretic exposure."},
                        "track_3_diagnostics": {"node_id": "V1_3", "title": "K+ 3.4 mEq/L [L]", "badge": "CLUE", "severity": "warning", "summary": "Spontaneous hypokalemia off diuretics.", "details": "Red flag for hyperaldosteronism."},
                        "track_4_open_loops": {"node_id": "V1_4", "title": "Secondary HTN Clue", "badge": "CONTEXT", "severity": "info", "summary": "Prompted Aug 2026 workup.", "details": "OSA also treated."},
                    },
                },
                {
                    "time_id": "T2",
                    "date": "2026-08-18",
                    "display_date": "Aug 14–18, 2026",
                    "phase": "Unreviewed ARR=95",
                    "tracks": {
                        "track_1_encounters": {"node_id": "V2_1", "title": "Secondary HTN Workup", "badge": "WORKUP", "severity": "info", "summary": "BP 165/104; PAC/Renin ordered.", "details": "Dr. S. Chen."},
                        "track_2_medications": {"node_id": "V2_2", "title": "Unchanged Regimen", "badge": "WAITING LABS", "severity": "normal", "summary": "Awaiting send-out endocrine panel.", "details": "No MRA started."},
                        "track_3_diagnostics": {"node_id": "V2_3", "title": "ARR = 95 [CRITICAL HIGH]", "badge": "CONN'S DX", "severity": "critical", "summary": "Aldosterone 28.5, Renin 0.3 (ARR 95 > 30).", "details": "Diagnostic for Primary Hyperaldosteronism."},
                        "track_4_open_loops": {"node_id": "V2_4", "title": "OPEN-302 Unreviewed Send-Out", "badge": "DROPPED", "severity": "critical", "summary": "Resulted 08/18 — never reviewed!", "details": "Left untreated for 12 weeks."},
                    },
                },
                {
                    "time_id": "T3",
                    "date": "2026-11-08",
                    "display_date": "Nov 08, 2026",
                    "phase": "ED Hypertensive Urgency",
                    "tracks": {
                        "track_1_encounters": {"node_id": "V3_1", "title": "ED Visit: BP 210/118", "badge": "ED URGENCY", "severity": "critical", "summary": "Severe occipital headache -> 164/96.", "details": "Given single KCl dose."},
                        "track_2_medications": {"node_id": "V3_2", "title": "NEW Chlorthalidone 25mg!", "badge": "UNSAFE RX", "severity": "critical", "summary": "Potassium-wasting thiazide added + Norvasc ↑10mg.", "details": "Missed ARR=95 & low K+."},
                        "track_3_diagnostics": {"node_id": "V3_3", "title": "ED K+ 3.2 [LL] | CT Head Neg", "badge": "LOW K+", "severity": "critical", "summary": "K+ already 3.2 BEFORE Chlorthalidone!", "details": "Cr 0.9 mg/dL."},
                        "track_4_open_loops": {"node_id": "V3_4", "title": "OPEN-301 Hypokalemia Hazard", "badge": "CRITICAL", "severity": "critical", "summary": "High risk of cardiac arrhythmia.", "details": "Thiazide + aldosterone K+ wasting."},
                    },
                },
                {
                    "time_id": "T4",
                    "date": "2026-11-12",
                    "display_date": "Nov 12, 2026 (Today)",
                    "phase": "Today's Triage Alert",
                    "tracks": {
                        "track_1_encounters": {"node_id": "V4_1", "title": "Triage: Calf Cramps & BP 168/102", "badge": "TODAY", "severity": "critical", "summary": "Symptomatic muscle cramps x2d (Denver ZIP 80203).", "details": "Acute hypokalemia symptoms."},
                        "track_2_medications": {"node_id": "V4_2", "title": "STOP Chlorthalidone → Start MRA", "badge": "STOP & SWITCH", "severity": "critical", "summary": "Stop Chlorthalidone; give KCl + start Spironolactone.", "details": "Targets root aldosterone excess."},
                        "track_3_diagnostics": {"node_id": "V4_3", "title": "STAT BMP/K+, 12-Lead ECG & Adrenal CT", "badge": "STAT ORDERS", "severity": "critical", "summary": "Check STAT K+ & QTc/U-waves; order Adrenal CT.", "details": "Adenoma vs. hyperplasia."},
                        "track_4_open_loops": {"node_id": "V4_4", "title": "Resolve OPEN-301 & OPEN-302", "badge": "CRITICAL", "severity": "critical", "summary": "1. Stop thiazide & STAT K+ 2. Adrenal CT + Endocrine.", "details": "Prevents arrhythmic arrest."},
                    },
                },
            ],
            "causal_links": [
                {"from": "V2_3", "to": "V2_4", "label": "ARR = 95 returned 08/18 confirming Conn's Syndrome but remained unreviewed"},
                {"from": "V2_4", "to": "V3_1", "label": "Untreated Primary Hyperaldosteronism drove BP 210/118 ED crisis"},
                {"from": "V3_3", "to": "V3_2", "label": "ED started Chlorthalidone 25mg despite K+ 3.2 mEq/L, causing today's calf cramps"},
            ],
        },
    },
]


def build_fhir_resources_for_patient(p: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Converts a patient cohort specification into ordered HL7 FHIR R4 resources."""
    pid = p["patient_id"]
    pat_ref = {"reference": f"Patient/{pid}"}
    out: list[tuple[str, str, dict[str, Any]]] = []

    # 1. Patient
    out.append(("Patient", pid, _build_patient_resource(p)))

    # 2. Today's Triage Encounter + Vital-Sign Observations
    triage = p["todays_triage"]
    t_enc_id = triage["encounter_id"]
    out.append(
        (
            "Encounter",
            t_enc_id,
            {
                "resourceType": "Encounter",
                "id": t_enc_id,
                "status": "in-progress",
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "EMER",
                    "display": "emergency",
                },
                "type": [{"text": triage["appointment_type"]}],
                "subject": pat_ref,
                "period": {"start": f"{triage['visit_date']}T08:30:00+00:00"},
                "reasonCode": [{"text": triage["chief_complaint"]}],
                "extension": [
                    {"url": f"{EXT_BASE}/ma-intake-note", "valueString": triage["ma_intake_note"]},
                    {"url": f"{EXT_BASE}/triage-vitals-json", "valueString": json.dumps(triage["vitals"])},
                ],
            },
        )
    )

    vitals_obs_id = f"obs-vitals-{pid}"
    out.append(
        (
            "Observation",
            vitals_obs_id,
            {
                "resourceType": "Observation",
                "id": vitals_obs_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "vital-signs",
                                "display": "Vital Signs",
                            }
                        ]
                    }
                ],
                "code": {"text": "Triage Vital Signs Panel"},
                "subject": pat_ref,
                "encounter": {"reference": f"Encounter/{t_enc_id}"},
                "effectiveDateTime": f"{triage['visit_date']}T08:35:00+00:00",
                "valueString": (
                    f"BP {triage['vitals']['bp']} | HR {triage['vitals']['hr']} | "
                    f"RR {triage['vitals']['rr']} | SpO2 {triage['vitals']['spo2']} | "
                    f"Temp {triage['vitals']['temp']} | Wt {triage['vitals']['weight_lbs']} lbs (BMI {triage['vitals']['bmi']})"
                ),
                "note": [{"text": triage["ma_intake_note"]}],
            },
        )
    )

    # 3. Past Hospitalizations, ED Visits & Specialist Consult Encounters + DocumentReferences
    for enc in p["encounters_and_notes"]:
        out.append(
            (
                "Encounter",
                enc["id"],
                {
                    "resourceType": "Encounter",
                    "id": enc["id"],
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": enc["class_code"],
                    },
                    "type": [{"text": enc["type"]}],
                    "subject": pat_ref,
                    "period": {"start": f"{enc['date']}T09:00:00+00:00"},
                    "reasonCode": [{"text": enc["primary_diagnosis"]}],
                    "serviceProvider": {"display": enc["facility"]},
                    "participant": [{"individual": {"display": enc["author"]}}],
                },
            )
        )
        out.append(
            (
                "DocumentReference",
                enc["doc_id"],
                {
                    "resourceType": "DocumentReference",
                    "id": enc["doc_id"],
                    "status": "current",
                    "type": {"text": enc["type"]},
                    "subject": pat_ref,
                    "date": f"{enc['date']}T15:00:00+00:00",
                    "author": [{"display": enc["author"]}],
                    "description": enc["primary_diagnosis"],
                    "content": [
                        {
                            "attachment": {
                                "contentType": "text/plain; charset=utf-8",
                                "data": _b64(enc["summary_note"]),
                                "title": f"{enc['type']} — {enc['facility']}",
                            }
                        }
                    ],
                    "context": {"encounter": [{"reference": f"Encounter/{enc['id']}"}]},
                },
            )
        )

    # 4. Allergies
    for al in p["allergies"]:
        out.append(
            (
                "AllergyIntolerance",
                al["id"],
                {
                    "resourceType": "AllergyIntolerance",
                    "id": al["id"],
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "criticality": al["criticality"],
                    "code": {"text": al["substance"]},
                    "patient": pat_ref,
                    "reaction": [
                        {
                            "manifestation": [{"text": al["reaction"]}],
                            "severity": al["severity"],
                        }
                    ],
                },
            )
        )

    # 5. Conditions (SNOMED-CT + ICD-10-CM)
    for c in p["conditions"]:
        cond_body: dict[str, Any] = {
            "resourceType": "Condition",
            "id": c["id"],
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": c["status"],
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed",
                    }
                ]
            },
            "code": {
                "coding": [
                    {"system": "http://snomed.info/sct", "code": c["snomed"], "display": c["display"]},
                    {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": c["icd10"], "display": c["display"]},
                ],
                "text": c["display"],
            },
            "subject": pat_ref,
            "onsetDateTime": c["onset"],
        }
        if c.get("abatement"):
            cond_body["abatementDateTime"] = c["abatement"]
        out.append(("Condition", c["id"], cond_body))

    # 6. Medications (Active, Held, Stopped, Completed + Adherence/Reconciliation Extensions)
    for m in p["medications"]:
        med_meta = {
            "prior_dose": m.get("prior_dose", "Unknown"),
            "change_type": m.get("change_type", ""),
            "actual_patient_adherence": m.get("adherence", ""),
            "hold_or_stop_reason": m.get("reason", ""),
            "reinitiation_criteria": m.get("reinitiation_criteria", ""),
        }
        med_body: dict[str, Any] = {
            "resourceType": "MedicationRequest",
            "id": m["id"],
            "status": m["status"],
            "intent": "order",
            "authoredOn": m["authored_on"],
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": m["rxcui"],
                        "display": m["coding_display"],
                    }
                ],
                "text": m["text"],
            },
            "subject": pat_ref,
            "dosageInstruction": [{"sequence": 1, "text": m["dosage"]}],
            "requester": {"display": m["prescriber"]},
            "extension": [
                {"url": f"{EXT_BASE}/med-reconciliation-json", "valueString": json.dumps(med_meta)}
            ],
        }
        if m.get("reason"):
            med_body["statusReason"] = {"text": m["reason"]}
        out.append(("MedicationRequest", m["id"], med_body))

    # 7. Longitudinal Laboratory Observations
    for lab in p["labs"]:
        for idx, h in enumerate(lab["history"], start=1):
            obs_id = f"{lab['id_prefix']}-{idx}"
            obs_body: dict[str, Any] = {
                "resourceType": "Observation",
                "id": obs_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": lab["loinc"], "display": lab["test"]}],
                    "text": lab["test"],
                },
                "subject": pat_ref,
                "effectiveDateTime": f"{h['date']}T08:00:00+00:00",
                "referenceRange": [{"text": lab["ref_range"]}],
                "interpretation": [{"text": h["flag"]}],
                "note": [{"text": h["context"]}],
            }
            if "value" in h:
                obs_body["valueQuantity"] = {"value": h["value"], "unit": lab["unit"]}
            else:
                obs_body["valueString"] = h["value_str"]
            out.append(("Observation", obs_id, obs_body))

    # 8. Diagnostic Imaging & Procedure Reports
    for img in p["imaging"]:
        out.append(
            (
                "DiagnosticReport",
                img["id"],
                {
                    "resourceType": "DiagnosticReport",
                    "id": img["id"],
                    "status": "final",
                    "category": [{"text": img["category"]}],
                    "code": {"text": img["modality"]},
                    "subject": pat_ref,
                    "effectiveDateTime": f"{img['date']}T11:00:00+00:00",
                    "conclusion": img["findings"],
                },
            )
        )

    # 9. Open Clinical Loops, Safety Alerts & Care Gaps (FHIR Flag resources)
    for fl in p["open_loops"]:
        flag_meta = {
            "item_id": fl["item_id"],
            "priority": fl["priority"],
            "category": fl["category"],
            "details": fl["details"],
        }
        out.append(
            (
                "Flag",
                fl["id"],
                {
                    "resourceType": "Flag",
                    "id": fl["id"],
                    "status": "active",
                    "category": [{"text": f"[{fl['priority']}] {fl['category']}"}],
                    "code": {"text": fl["details"]},
                    "subject": pat_ref,
                    "extension": [
                        {"url": f"{EXT_BASE}/open-loop-json", "valueString": json.dumps(flag_meta)}
                    ],
                },
            )
        )

    return out


def get_emergency_ward_resources() -> list[tuple[str, str, dict[str, Any]]]:
    """Returns all FHIR R4 resources across `pat-001` through `pat-007` in referential-integrity order."""
    all_res: list[tuple[str, str, dict[str, Any]]] = []
    for spec in RAW_COHORT_SPECS:
        all_res.extend(build_fhir_resources_for_patient(spec))
    return all_res


def build_fallback_bundles() -> dict[str, dict[str, Any]]:
    """Builds `Patient/$everything` FHIR Bundle dictionaries for `pat-001` through `pat-007`."""
    bundles: dict[str, dict[str, Any]] = {}
    for spec in RAW_COHORT_SPECS:
        pid = spec["patient_id"]
        entries = [
            {"resource": body}
            for _, _, body in build_fhir_resources_for_patient(spec)
        ]
        bundles[pid] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": entries,
        }
    return bundles
