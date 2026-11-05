"""Google ADK Multi-Agent Architecture for Longitudinal EHR Chart Summarization.

Architecture Overview:
1. `root_agent` (Clinical Pre-Chart Coordinator - LlmAgent):
   - Can list today's clinic schedule (`list_scheduled_patients`)
   - Delegates full longitudinal chart reviews to `chart_review_pipeline` (`SequentialAgent`)

2. `chart_review_pipeline` (`SequentialAgent`):
   - Step 1: `intake_and_triage_agent` (`LlmAgent`)
     Fetches patient demographics, allergies, active problems, and today's triage intake
     to anchor the entire chart review around today's chief complaint.
   - Step 2: `parallel_ehr_domain_agents` (`ParallelAgent`)
     Concurrently executes 4 specialized clinical agents across EHR compartments:
       a) `hospitalization_notes_agent` -> Recent admissions, ED visits & consults
       b) `medication_reconciliation_agent` -> Med changes, held drugs & adherence barriers
       c) `labs_imaging_trend_agent` -> Longitudinal lab trajectories & incidental imaging
       d) `open_loops_care_gaps_agent` -> Dropped follow-ups, unreviewed labs & safety alerts
   - Step 3: `pre_chart_brief_synthesizer` (`LlmAgent`)
     Synthesizes findings from all 4 domain agents into a tailored, 1-page Physician Pre-Chart Brief.
"""

import os
import ssl
import warnings
import certifi
import google.auth

if not os.environ.get("SSL_CERT_FILE") and ssl.get_default_verify_paths().cafile is None:
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .tools import (
    generate_clinical_swimlane_graph,
    get_hospitalizations_and_clinical_notes,
    get_longitudinal_labs_and_imaging,
    get_medication_reconciliation_history,
    get_open_loops_and_care_gaps,
    get_patient_demographics_and_triage,
    list_scheduled_patients,
)


def configure_gcp_sso_vertex_ai() -> str | None:
    """Configures Google GenAI / ADK to authenticate via GCP SSO (ADC + Vertex AI)."""
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return None

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project_id:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                _, detected_project = google.auth.default()
                project_id = detected_project
            except Exception:
                project_id = None

    if project_id:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    return project_id


ACTIVE_GCP_PROJECT = configure_gcp_sso_vertex_ai()
MODEL_NAME = os.environ.get("ADK_MODEL", "gemini-3.8-flash")

# ---------------------------------------------------------------------------
# Stage 1: Patient Intake & Triage Context Agent
# ---------------------------------------------------------------------------
intake_and_triage_agent = LlmAgent(
    name="intake_and_triage_agent",
    model=MODEL_NAME,
    description="Retrieves patient demographics, allergies, active problem list, and today's triage vitals/chief complaint.",
    instruction="""You are the Clinical Intake & Triage Agent.
Identify the target patient from the conversation context (e.g., PAT-1001, PAT-1002, PAT-1003, or by patient name)
and call `get_patient_demographics_and_triage`.

Summarize clearly:
1. Patient ID, Name, Age, Sex, and severe Allergies.
2. Active Problem List (with ICD-10 codes).
3. Today's Visit Reason (Chief Complaint), Triage Vitals, and Medical Assistant (MA) Intake Notes.
Keep your summary concise and structured so downstream specialist agents know what clinical questions to prioritize.""",
    tools=[get_patient_demographics_and_triage, list_scheduled_patients],
    output_key="patient_intake_context",
)

# ---------------------------------------------------------------------------
# Stage 2 (Parallel): 4 Specialized EHR Compartment Agents
# ---------------------------------------------------------------------------
hospitalization_notes_agent = LlmAgent(
    name="hospitalization_notes_agent",
    model=MODEL_NAME,
    description="Analyzes inpatient discharge summaries, ED visits, and specialist consult notes.",
    instruction="""You are the Hospitalization & Specialist Notes Agent.
Patient Context so far:
{patient_intake_context}

Call `get_hospitalizations_and_clinical_notes` for this patient and extract:
- Recent hospitalizations or ED visits (dates, facility, primary diagnosis, clinical course, admission vs. discharge weight/status).
- Specific specialist consult recommendations and criteria for outpatient medication titration or follow-up.
- Any incidental findings mentioned in discharge or consult notes.
Cite exact encounter dates and authors.""",
    tools=[get_hospitalizations_and_clinical_notes],
    output_key="encounters_summary",
)

medication_reconciliation_agent = LlmAgent(
    name="medication_reconciliation_agent",
    model=MODEL_NAME,
    description="Performs longitudinal medication reconciliation, tracking dose changes, held drugs, and adherence barriers.",
    instruction="""You are the Clinical Pharmacist & Medication Reconciliation Agent.
Patient Context so far:
{patient_intake_context}

Call `get_medication_reconciliation_history` for this patient and extract:
- Recent medication changes (NEW starts, DOSE increases/decreases) with dates and reasons.
- Medications currently HELD or DISCONTINUED (why they were held and the exact clinical criteria required to safely resume them).
- Real-world adherence discrepancies (e.g., self-titration, prior authorization rejections, high copays, or drug-drug absorption interactions like iron + levothyroxine).
Be explicit about discrepancies between what is prescribed in the EHR vs. what the patient is actually taking.""",
    tools=[get_medication_reconciliation_history],
    output_key="medication_summary",
)

labs_imaging_trend_agent = LlmAgent(
    name="labs_imaging_trend_agent",
    model=MODEL_NAME,
    description="Analyzes multi-year lab trajectories and diagnostic imaging reports.",
    instruction="""You are the Longitudinal Diagnostics & Lab Trend Agent.
Patient Context so far:
{patient_intake_context}

Call `get_longitudinal_labs_and_imaging` for this patient and analyze:
- Key longitudinal lab trajectories showing Baseline -> Hospital/Prior Peak -> Latest Pre-Visit Value (with dates and reference flags).
- Highlight whether acute abnormalities (e.g., AKI, transaminitis, hypokalemia, elevated NT-proBNP, TSH, or ARR) are resolving or worsening.
- Key findings from Echocardiograms, CTs, or other imaging, paying special attention to incidental findings requiring follow-up.""",
    tools=[get_longitudinal_labs_and_imaging],
    output_key="diagnostics_summary",
)

open_loops_care_gaps_agent = LlmAgent(
    name="open_loops_care_gaps_agent",
    model=MODEL_NAME,
    description="Identifies unresolved clinical open loops, unreviewed results, missed appointments, and care gaps.",
    instruction="""You are the Clinical Safety & Open-Loop Tracker Agent.
Patient Context so far:
{patient_intake_context}

Call `get_open_loops_and_care_gaps` for this patient and identify:
- CRITICAL & HIGH priority open loops (e.g., unreviewed diagnostic tests, drug-lab toxicity alerts, held medications ready for restart, or unordered follow-up imaging for incidental nodules).
- Missed specialty appointments or pending pre-biologic screenings.
- Preventive care gaps.""",
    tools=[get_open_loops_and_care_gaps],
    output_key="open_loops_summary",
)

parallel_ehr_domain_agents = ParallelAgent(
    name="parallel_ehr_domain_agents",
    description="Runs 4 specialized EHR compartment agents concurrently to analyze notes, medications, labs/imaging, and open loops.",
    sub_agents=[
        hospitalization_notes_agent,
        medication_reconciliation_agent,
        labs_imaging_trend_agent,
        open_loops_care_gaps_agent,
    ],
)

# ---------------------------------------------------------------------------
# Stage 3: Chief Medical Synthesizer (1-Page Pre-Chart Brief + Swimlane Graph)
# ---------------------------------------------------------------------------
pre_chart_brief_synthesizer = LlmAgent(
    name="pre_chart_brief_synthesizer",
    model=MODEL_NAME,
    description="Synthesizes multi-agent EHR findings and the Interactive Multi-Track Clinical Swimlane Graph into a 1-page physician pre-chart summary.",
    instruction="""You are the Chief Medical Summarizer preparing a 1-Page Pre-Chart Brief for the attending physician right before they walk into the exam room.

First, call `generate_clinical_swimlane_graph` for this patient to synchronize the four parallel temporal tracks along a shared horizontal timeline and generate the interactive HTML/SVG swimlane graph.

Synthesize the structured findings gathered by the clinical agent team:
- **Patient Intake & Triage Context**:
{patient_intake_context}

- **Hospitalizations & Specialist Notes Analysis**:
{encounters_summary}

- **Medication Reconciliation Analysis**:
{medication_summary}

- **Longitudinal Labs & Imaging Trends**:
{diagnostics_summary}

- **Unresolved Open Loops & Safety Alerts**:
{open_loops_summary}

Format your output as a clean, scannable **1-PAGE PHYSICIAN PRE-CHART BRIEF** using Markdown with the following sections:
1. **Header & Visit Snapshot**: Patient Name, ID, Age/Sex, Allergies (bold any severe allergies), Today's Chief Complaint, and Today's Key Vitals (highlighting weight/BP changes).
2. **Clinical Synthesis ("Why the Patient is Here Today")**: A 2-3 sentence executive synthesis connecting recent events, medication adherence/changes, and lab trends to today's presentation.
3. **Interactive Multi-Track Clinical Swimlane Graph (4 Synchronized Temporal Tracks)**:
   - Include the exact `mermaid_swimlane` diagram returned by `generate_clinical_swimlane_graph` so the 4 parallel tracks render along a shared horizontal timeline.
   - Include the `markdown_swimlane_matrix` table synchronizing **Track 1 (Encounters & Notes)**, **Track 2 (Medications & Adherence)**, **Track 3 (Labs, Vitals & Imaging)**, and **Track 4 (Open Loops & Safety Alerts)** across shared chronological timepoints, along with the **Cross-Track Temporal Causal Links** and the `interactive_html_path`.
4. **Recent Hospitalizations, ED Visits & Specialist Consults**: Bullet points with exact dates, diagnoses, and specialist guidance.
5. **Medication Reconciliation & Adherence Alerts**: Markdown table or structured bullets distinguishing:
   - *Recent Starts / Dose Changes & Actual Patient Adherence*
   - *Held / Discontinued Medications & Criteria to Resume*
6. **Key Longitudinal Lab & Imaging Trajectories**: Markdown table showing `Test | Baseline | Peak / Prior | Latest (Date) | Clinical Interpretation`, plus key imaging findings.
7. **Unresolved Issues ("Open Loops") & Prioritized Action Plan for Today's Visit**: Numbered, high-impact clinical checklist the physician can act on immediately during today's encounter.""",
    tools=[generate_clinical_swimlane_graph],
    output_key="final_pre_chart_brief",
)

# ---------------------------------------------------------------------------
# Sequential Pipeline combining Intake -> Parallel Domain Review -> Synthesis
# ---------------------------------------------------------------------------
chart_review_pipeline = SequentialAgent(
    name="chart_review_pipeline",
    description=(
        "Executes a complete multi-agent longitudinal chart review for a specific patient: "
        "(1) Intake & triage context, (2) Parallel investigation of hospitalizations, medications, "
        "labs/imaging, and open loops, and (3) Synthesis of a 1-page physician pre-chart brief "
        "with an Interactive Multi-Track Clinical Swimlane Graph."
    ),
    sub_agents=[
        intake_and_triage_agent,
        parallel_ehr_domain_agents,
        pre_chart_brief_synthesizer,
    ],
)

# ---------------------------------------------------------------------------
# Root Agent: Entry point for `adk web`, `adk run`, and programmatic runners
# ---------------------------------------------------------------------------
root_agent = LlmAgent(
    name="pre_chart_coordinator",
    model=MODEL_NAME,
    description="Coordinator agent for longitudinal EHR chart summarization, multi-track clinical swimlane graphs, and clinic schedule lookup.",
    instruction="""You are the AI Pre-Chart Coordinator assisting Dr. Sarah Chen in her outpatient clinic.

- If the physician asks who is on today's clinic schedule or what patients are available, call `list_scheduled_patients` and present a clear overview of the patients (`PAT-1001`, `PAT-1002`, `PAT-1003`).
- If the physician asks specifically for the Interactive Multi-Track Clinical Swimlane Graph for a patient without a full chart review, you may call `generate_clinical_swimlane_graph` directly and display both the `mermaid_swimlane` and `markdown_swimlane_matrix` along with the `interactive_html_path`.
- Whenever the physician asks to summarize a chart, prepare a pre-chart brief, or review a specific patient (by ID like `PAT-1001` or by name like `Arthur Pendelton`, `Elena Rostova`, or `Marcus Vance`), immediately transfer/delegate to `chart_review_pipeline` so the multi-agent team performs a comprehensive longitudinal chart review including the Interactive Multi-Track Clinical Swimlane Graph.""",
    tools=[list_scheduled_patients, generate_clinical_swimlane_graph],
    sub_agents=[chart_review_pipeline],
)
