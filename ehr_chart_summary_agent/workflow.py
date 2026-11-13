"""
Google ADK 2.0 Graph-Based Workflow (`google.adk.workflow.Workflow`) for Emergency Ward Triage.

Demonstrates ADK 2.0's graph orchestration engine:
  START -> fhir_intake_node -> (brand_generic_node, outbreak_surveillance_node) -> clinical_correlation_node
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.workflow import START, Workflow

from .clinical_tools import (
    check_drug_brand_or_generic,
    get_location_outbreak_and_disease_data,
    get_patient_clinical_profile,
)

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.8-flash")

fhir_intake_node = LlmAgent(
    name="fhir_intake_node",
    model=MODEL_NAME,
    mode="single_turn",
    description="Retrieves patient FHIR ($everything) profile, conditions, medications, location, and FHIR citations.",
    instruction=(
        "Extract the patient_id and patient_name from the physician's query and call "
        "`get_patient_clinical_profile(patient_id, patient_name)`. Return the complete structured "
        "patient demographics, location (city, state, coordinates), current medications, "
        "previous medications, active conditions, previous conditions, and all FHIR resource citations."
    ),
    tools=[get_patient_clinical_profile],
    output_key="fhir_intake_state",
)

brand_generic_node = LlmAgent(
    name="brand_generic_node",
    model=MODEL_NAME,
    mode="single_turn",
    description="Checks Original/Generic vs. Brand Name, drug uses, and known side effects via RxNorm and OpenFDA with citations.",
    instruction=(
        "Using the medications in `{fhir_intake_state}`, call `check_drug_brand_or_generic` "
        "for each current and previous medication. Report whether each drug in FHIR is an "
        "ORIGINAL_GENERIC_NAME or BRAND_NAME, its active generic ingredient(s), brand equivalents, "
        "duplicate ingredient risks, clinical uses (`openfda_drug_uses`), known side effects and warnings "
        "(`openfda_known_side_effects`), and the exact RxNorm and OpenFDA citations."
    ),
    tools=[check_drug_brand_or_generic],
    output_key="brand_generic_state",
)

outbreak_surveillance_node = LlmAgent(
    name="outbreak_surveillance_node",
    model=MODEL_NAME,
    mode="single_turn",
    description="Queries CDC PLACES ZCTA5 (qnzd-25i4), CDC NSSP Local ED (rdmq-nq56), CDC NWSS Wastewater, and Air Quality strictly for the patient's 5-digit ZIP code.",
    instruction=(
        "Using the patient's 5-digit `postal_code` (ZIP code), `latitude`, `longitude`, and `city` in `{fhir_intake_state}`, "
        "call `get_location_outbreak_and_disease_data(postal_code, latitude, longitude, city)`. "
        "Summarize active outbreaks in the ZIP code's local ED & sewershed catchment, persistent diseases strictly inside "
        "that 5-digit ZIP code, hyperlocal air quality triggers, and all source citations. Do NOT report statewide summaries."
    ),
    tools=[get_location_outbreak_and_disease_data],
    output_key="outbreak_surveillance_state",
)

clinical_correlation_node = LlmAgent(
    name="clinical_correlation_node",
    model=MODEL_NAME,
    mode="single_turn",
    description="Synthesizes FHIR history, drug brand/generic uses & side effects, and hyperlocal ZIP-code disease outbreaks with citations.",
    instruction="""
Synthesize the findings from:
- Patient FHIR Clinical Record: `{fhir_intake_state}`
- Medication Brand vs. Generic, Uses & Known Side Effects Analysis: `{brand_generic_state}`
- Patient ZIP-Code Outbreak & Persistent Disease Surveillance: `{outbreak_surveillance_state}`

CRITICAL REQUIREMENT: For EVERY piece of information you provide, you MUST include the inline citation from the tool outputs, plus a consolidated **Sources & Citations** section at the end. Links/URLs for FHIR datasets are NOT needed (cite FHIR data by source name and resource ID only, e.g., `Patient/<id>`, `Condition/<id>`, `MedicationRequest/<id>`).

Produce a structured **Emergency Ward Physician Clinical Correlation Report**:
1. **Patient Identity & Location Verification** (ID, Name match status, Age/Gender, Address & 5-Digit ZIP Code — with FHIR `Patient/<id>` citation, no URL needed)
2. **Medical History Summary** (Active Conditions vs. Previous/Resolved Conditions, Allergies — with FHIR `Condition/<id>`, SNOMED-CT code, and `AllergyIntolerance/<id>` citations, no URL needed)
3. **Medication Audit (Original/Generic vs. Brand Name, Uses, & Known Side Effects)**:
   - Current Medications vs. Previous Medications (with FHIR `MedicationRequest/<id>` citations, no FHIR URL needed)
   - For each drug:
     * FHIR Prescribed Name, RxCUI, and **Original/Generic vs. Brand Classification** (with NIH NLM RxNorm REST API citation)
     * **Active Ingredient(s)**, **Brand Equivalents**, and **Duplicate Therapy Warnings**
     * **Uses of the Drug** (`indications_and_usage`, `purpose`, `pharmacologic_class_epc` — with OpenFDA Drug Labeling API / DailyMed SPL citation `https://open.fda.gov/apis/drug/`)
     * **Known Side Effects & Warnings** (`labeled_adverse_reactions`, `warnings_and_cautions`, `contraindications`, `boxed_warning_excerpt` from OpenFDA SPL Label + `top_faers_reported_adverse_events` from OpenFDA FAERS API, with both citations)
4. **Hyperlocal Patient ZIP-Code Outbreak & Disease Context (Strictly ZIP `<postal_code>` Only)**:
   - Active local ED respiratory outbreak trajectories (`CDC NSSP rdmq-nq56`) and local sewershed pathogen detections (`CDC NWSS Wastewater`) serving the patient's ZIP code
   - Persistent chronic/endemic disease prevalence strictly inside the patient's 5-digit ZIP code (`CDC PLACES ZCTA5 qnzd-25i4`) and hyperlocal ZIP AQI (`Open-Meteo`)
5. **Emergency Ward Clinical Correlation & Differential Considerations**:
   - Correlate the presenting issue with past/active conditions, current/previous medication uses and known side effects, and active outbreaks inside the patient's ZIP code.
6. **Sources & Citations**:
   - Complete numbered list of all FHIR resource IDs (no FHIR links) and external API URLs (NIH RxNorm, OpenFDA, CDC PLACES ZCTA5, CDC NSSP Local ED, CDC NWSS Local Sewershed, Open-Meteo).
""",
    output_key="clinical_correlation_report",
)

emergency_triage_workflow = Workflow(
    name="emergency_triage_workflow",
    description=(
        "Google ADK 2.0 Graph Workflow for Emergency Ward Patient Triage: "
        "FHIR intake -> parallel (RxNorm Brand/Generic + OpenFDA Uses/Side Effects check "
        "& CDC NNDSS/FluView outbreak surveillance) -> Clinical Correlation with Citations."
    ),
    edges=[
        (
            START,
            fhir_intake_node,
            (brand_generic_node, outbreak_surveillance_node),
            clinical_correlation_node,
        )
    ],
)
