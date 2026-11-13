"""
FHIR-Backed Longitudinal EHR Chart Summarizer Multi-Agent Pipeline (Google ADK).

Ports `MedicalChartAgent`'s Sequential + Parallel Multi-Agent Architecture onto live
HL7 FHIR R4 resources (`synthe_data`) + NIH RxNorm / OpenFDA medication intelligence:
1. `intake_and_triage_agent` -> `patient_intake_context`
2. `parallel_ehr_domain_agents` (`ParallelAgent`):
   - `hospitalization_notes_agent` -> `encounters_summary`
   - `medication_reconciliation_agent` -> `medication_summary`
   - `labs_imaging_trend_agent` -> `diagnostics_summary`
   - `open_loops_care_gaps_agent` -> `open_loops_summary`
3. `pre_chart_brief_synthesizer` -> 1-Page Physician Chart Brief + 4-Track Clinical Swimlane Graph
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from ...clinical_tools import check_drug_brand_or_generic, list_emergency_ward_patients
from ...ehr_chart_tools import (
    generate_clinical_swimlane_graph,
    get_hospitalizations_and_clinical_notes,
    get_longitudinal_labs_and_imaging,
    get_medication_reconciliation_history,
    get_open_loops_and_care_gaps,
    get_patient_demographics_and_triage,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.8-flash")

# ---------------------------------------------------------------------------
# Stage 1: Patient Intake & Triage Context Agent (FHIR Patient + Encounter)
# ---------------------------------------------------------------------------
intake_and_triage_agent = LlmAgent(
    name="intake_and_triage_agent",
    model=MODEL_NAME,
    description=(
        "Retrieves FHIR patient demographics, 5-digit ZIP code, allergies, active problem list "
        "(SNOMED/ICD-10), and today's Emergency Ward triage vitals & chief complaint."
    ),
    instruction="""You are the Clinical Intake & Triage Agent.
Identify the target patient from the conversation context (e.g., `pat-001` through `pat-007`, legacy `PAT-1001`..`PAT-1003`, or patient name)
and call `get_patient_demographics_and_triage(patient_id)`.

Summarize concisely (cite FHIR resource IDs like `Patient/<id>`, `Encounter/<id>`, `Condition/<id>`, `AllergyIntolerance/<id>` — do NOT include links/URLs for FHIR datasets):
1. Canonical FHIR `patient_id`, Full Name, Age, Sex, 5-Digit ZIP Code (`postal_code`), and Allergies.
2. Active Problem List (with ICD-10 & SNOMED codes).
3. Today's Chief Complaint, Triage Vitals, and MA/Nurse Intake Note.""",
    tools=[get_patient_demographics_and_triage, list_emergency_ward_patients],
    output_key="patient_intake_context",
)

# ---------------------------------------------------------------------------
# Stage 2 (Parallel): 4 Specialized FHIR Compartment Agents
# ---------------------------------------------------------------------------
hospitalization_notes_agent = LlmAgent(
    name="hospitalization_notes_agent",
    model=MODEL_NAME,
    description="Analyzes FHIR inpatient discharge summaries, prior ED visits, and specialist consult notes.",
    instruction="""You are the Hospitalization & Specialist Notes Agent.
Patient Context so far:
{patient_intake_context}

Call `get_hospitalizations_and_clinical_notes(patient_id)` for this patient and extract:
- Recent hospitalizations, ED visits, and outpatient consults (dates, facility, author, primary diagnosis, clinical course).
- Specific specialist consult recommendations and outpatient medication titration / restart thresholds.
- Any incidental imaging or diagnostic findings noted in discharge/consult summaries.
Cite exact FHIR resource IDs (`Encounter/<id>`, `DocumentReference/<id>` — no FHIR URLs).""",
    tools=[get_hospitalizations_and_clinical_notes],
    output_key="encounters_summary",
)

medication_reconciliation_agent = LlmAgent(
    name="medication_reconciliation_agent",
    model=MODEL_NAME,
    description=(
        "Performs longitudinal FHIR medication reconciliation (dose changes, held drugs, adherence) "
        "combined with NIH RxNorm Original Drug vs. Brand Name verification and OpenFDA adverse effects."
    ),
    instruction="""You are the Clinical Pharmacist & Medication Reconciliation Agent.
Patient Context so far:
{patient_intake_context}

1. Call `get_medication_reconciliation_history(patient_id)` to fetch active, changed, and held/stopped FHIR `MedicationRequest` records.
2. Call `check_drug_brand_or_generic(drug_name, rxcui_code)` for the key medications to verify **ORIGINAL DRUG NAME (GENERIC)** vs. **BRAND NAME**, clinical uses, and OpenFDA adverse effects/warnings.
3. Report clearly:
   - Each medication's **ORIGINAL DRUG NAME (GENERIC) vs. BRAND NAME** status (with NIH RxNorm citation URL) and **OpenFDA Uses & Adverse Effects/Warnings** (with OpenFDA citation URLs).
   - Recent medication changes (`NEW START`, `DOSE INCREASED`), HELD/STOPPED medications with exact clinical criteria to resume, and real-world adherence barriers (self-titration, Prior Authorization blocks, duplicate active ingredients, or absorption/CYP interactions).
   - Cite FHIR `MedicationRequest/<id>` without FHIR URLs.""",
    tools=[get_medication_reconciliation_history, check_drug_brand_or_generic],
    output_key="medication_summary",
)

labs_imaging_trend_agent = LlmAgent(
    name="labs_imaging_trend_agent",
    model=MODEL_NAME,
    description="Analyzes multi-timepoint FHIR lab biomarker trajectories and DiagnosticReport imaging studies.",
    instruction="""You are the Longitudinal Diagnostics & Lab Trend Agent.
Patient Context so far:
{patient_intake_context}

Call `get_longitudinal_labs_and_imaging(patient_id)` for this patient and analyze:
- Key longitudinal lab trajectories (`Baseline -> Hospital/Prior Peak -> Latest Value` with dates, reference ranges, and `H`/`HH`/`L`/`LL` flags).
- Whether acute abnormalities (e.g., AKI, transaminitis, hypokalemia, supratherapeutic INR, rhabdomyolysis CK, anemia, elevated NT-proBNP, TSH, or ARR) are resolving or worsening.
- Key findings from DiagnosticReport imaging (`TTE`, `CT Chest`, `CT Head`, `CXR`, `Renal US`), highlighting any incidental findings requiring follow-up.
Cite FHIR `Observation/<id>` and `DiagnosticReport/<id>` resource IDs (no FHIR URLs).""",
    tools=[get_longitudinal_labs_and_imaging],
    output_key="diagnostics_summary",
)

open_loops_care_gaps_agent = LlmAgent(
    name="open_loops_care_gaps_agent",
    model=MODEL_NAME,
    description="Identifies unresolved clinical open loops, unreviewed labs, safety alerts, and care gaps from FHIR Flag resources.",
    instruction="""You are the Clinical Safety & Open-Loop Tracker Agent.
Patient Context so far:
{patient_intake_context}

Call `get_open_loops_and_care_gaps(patient_id)` for this patient and identify:
- `CRITICAL` and `HIGH` priority open clinical loops (drug-lab toxicity alerts, unreviewed send-out labs, held medications ready to restart, duplicate therapy hazards, or unordered follow-up imaging).
- `MEDIUM` and `LOW` missed specialty appointments and preventive care gaps.
Cite FHIR `Flag/<id>` resource IDs (no FHIR URLs).""",
    tools=[get_open_loops_and_care_gaps],
    output_key="open_loops_summary",
)

parallel_ehr_domain_agents = ParallelAgent(
    name="parallel_ehr_domain_agents",
    description=(
        "Runs 4 specialized FHIR compartment agents concurrently to analyze hospitalizations/notes, "
        "medication reconciliation + RxNorm/OpenFDA, longitudinal labs/imaging, and open loops."
    ),
    sub_agents=[
        hospitalization_notes_agent,
        medication_reconciliation_agent,
        labs_imaging_trend_agent,
        open_loops_care_gaps_agent,
    ],
)

# ---------------------------------------------------------------------------
# Stage 3: Chief Medical Synthesizer (1-Page Chart Brief + 4-Track Swimlane)
# ---------------------------------------------------------------------------
pre_chart_brief_synthesizer = LlmAgent(
    name="pre_chart_brief_synthesizer",
    model=MODEL_NAME,
    description=(
        "Synthesizes multi-agent FHIR findings and the Interactive 4-Track Clinical Swimlane Graph "
        "into a 1-Page Physician Chart Brief with citations and Suggested Next Steps."
    ),
    instruction="""You are the Chief Medical Summarizer preparing a **1-Page Physician Chart Brief** for the Emergency Ward physician.

First, call `generate_clinical_swimlane_graph(patient_id)` for this patient to synchronize the 4 parallel FHIR temporal tracks along a shared horizontal timeline and generate the interactive HTML/SVG swimlane viewer.

Synthesize the structured findings gathered by the clinical agent team:
- **Patient Intake & Triage Context**:
{patient_intake_context}

- **Hospitalizations & Specialist Notes Analysis**:
{encounters_summary}

- **Medication Reconciliation, Brand/Generic & Adverse Effects Analysis**:
{medication_summary}

- **Longitudinal Labs & Imaging Trends**:
{diagnostics_summary}

- **Unresolved Open Loops & Safety Alerts**:
{open_loops_summary}

Format your output as a clean, scannable **1-PAGE PHYSICIAN CHART BRIEF** in Markdown:
1. **Header & Triage Snapshot**: Patient Name, ID, Age/Sex, 5-Digit ZIP Code, Allergies (bold high-criticality allergies), Today's Chief Complaint, and Today's Key Vitals & Triage Note.
2. **Executive Clinical Synthesis ("Why the Patient is Here Today")**: 2-3 sentences connecting recent encounters, medication changes/adherence/adverse effects, and lab trajectories to today's presentation.
3. **Interactive Multi-Track Clinical Swimlane Graph (4 Synchronized FHIR Tracks)**:
   - Include the exact `mermaid_swimlane` diagram returned by `generate_clinical_swimlane_graph`.
   - Include the `markdown_swimlane_matrix` table synchronizing **Track 1 (Encounters & Notes)**, **Track 2 (Medications & Adherence)**, **Track 3 (Labs, Vitals & Imaging)**, and **Track 4 (Open Loops & Safety Alerts)** along with the **Cross-Track Temporal Causal Links** and the `interactive_html_path`.
4. **Recent Hospitalizations, ED Visits & Specialist Consults**: Concise bullets with dates, diagnoses, and specialist guidance.
5. **Medication Reconciliation, Drug vs. Brand Name & Adverse Effects**: Distinguish *Active / Changed Prescriptions & Adherence* vs. *Held / Discontinued Medications & Restart Criteria*, explicitly noting **ORIGINAL DRUG NAME (GENERIC) vs. BRAND NAME** (RxNorm) and key **OpenFDA Adverse Effects/Warnings**.
6. **Key Longitudinal Lab & Imaging Trajectories**: Markdown table (`Test | Ref Range | Baseline -> Peak/Prior -> Latest | Interpretation`) + imaging findings.
7. **Unresolved Issues ("Open Loops") & Prioritized Action Plan for Today**: Numbered bedside action checklist.
8. **Sources & Citations**: FHIR resource IDs (no FHIR links) + clickable URLs for NIH RxNorm and OpenFDA.
9. **Suggested Next Steps**: Offer clear next options (e.g., checking **Hyperlocal Outbreak & Disease Surveillance in the patient's 5-digit ZIP code**, drilling into a specific medication interaction, or switching to another ward patient `pat-001`–`pat-007`).""",
    tools=[generate_clinical_swimlane_graph],
    output_key="final_pre_chart_brief",
)

chart_review_pipeline = SequentialAgent(
    name="chart_review_pipeline",
    description=(
        "Executes a full multi-agent longitudinal FHIR chart review (`SequentialAgent` + `ParallelAgent`): "
        "(1) Intake & triage context, (2) Parallel analysis of hospitalizations/notes, medication reconciliation "
        "(+ RxNorm/OpenFDA), longitudinal labs/imaging, and open loops, and (3) Synthesis of a 1-Page Physician "
        "Chart Brief with an Interactive 4-Track Clinical Swimlane Graph."
    ),
    sub_agents=[
        intake_and_triage_agent,
        parallel_ehr_domain_agents,
        pre_chart_brief_synthesizer,
    ],
)
