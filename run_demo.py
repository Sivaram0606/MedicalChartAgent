"""Runner script for the Google ADK Longitudinal EHR Chart Summarizer.

Supports two execution modes:
1. Live Google ADK Execution (`InMemoryRunner` with Gemini via `GOOGLE_API_KEY` or Vertex AI)
2. Local Agentic Trace & Synthesis Mode (automatically used if no API credentials are set,
   or via `--offline`), which executes the exact same 3-stage agentic tool pipeline
   against the mock EHR database and prints the agent execution trace + 1-Page Pre-Chart Brief.
"""

import argparse
import asyncio
import os
import ssl
import certifi

if not os.environ.get("SSL_CERT_FILE") and ssl.get_default_verify_paths().cafile is None:
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from google.genai import types

from ehr_chart_summarizer.agent import chart_review_pipeline
from ehr_chart_summarizer.tools import (
    generate_clinical_swimlane_graph,
    get_hospitalizations_and_clinical_notes,
    get_longitudinal_labs_and_imaging,
    get_medication_reconciliation_history,
    get_open_loops_and_care_gaps,
    get_patient_demographics_and_triage,
    list_scheduled_patients,
)


async def run_live_adk_pipeline(patient_id: str) -> None:
    """Runs the live Google ADK `chart_review_pipeline` using `InMemoryRunner`."""
    from google.adk.runners import InMemoryRunner

    swimlane_info = generate_clinical_swimlane_graph(patient_id)
    runner = InMemoryRunner(
        agent=chart_review_pipeline,
        app_name="ehr_chart_summarizer",
    )
    session = await runner.session_service.create_session(
        app_name="ehr_chart_summarizer",
        user_id="dr_sarah_chen",
    )

    prompt = (
        f"Generate a complete 1-page longitudinal pre-chart summary for patient {patient_id} "
        f"for today's clinic visit, including the Interactive Multi-Track Clinical Swimlane Graph."
    )
    print(f"\n[ADK Live Runner] Starting Multi-Agent Pipeline for {patient_id}...\n")

    user_msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    final_output = ""
    async for event in runner.run_async(
        user_id="dr_sarah_chen",
        session_id=session.id,
        new_message=user_msg,
    ):
        author = getattr(event, "author", "agent")
        if event.get_function_calls():
            for fc in event.get_function_calls():
                print(f"  -> [{author}] invoking tool: {fc.name}({fc.args})")
        if event.is_final_response() and event.content and event.content.parts:
            text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
            if text_parts:
                text = "\n".join(text_parts)
                print(f"  ✓ [{author}] completed stage output.")
                if author == "pre_chart_brief_synthesizer":
                    final_output = text

    if final_output:
        print("\n" + "=" * 88)
        print(final_output)
        print("=" * 88)
    if swimlane_info.get("status") == "success":
        print(f"\n[Interactive Multi-Track Clinical Swimlane HTML]: {swimlane_info['interactive_html_path']}\n")


def run_deterministic_agentic_pipeline(patient_id: str) -> None:
    """Executes the 3-stage ADK agentic workflow deterministically and formats the 1-page brief."""
    print("=" * 88)
    print(" GOOGLE ADK MULTI-AGENT EXECUTION TRACE: LONGITUDINAL CHART SUMMARIZER")
    print("=" * 88)

    # Stage 1: Intake & Triage Agent
    print(f"\n[Stage 1: intake_and_triage_agent]")
    print(f"  ├─ Calling tool: get_patient_demographics_and_triage(patient_id='{patient_id}')")
    intake = get_patient_demographics_and_triage(patient_id)
    if intake.get("status") != "success":
        print(f"Error: {intake.get('message')}")
        return

    demo = intake["demographics"]
    visit = intake["todays_visit"]
    vitals = visit["triage_vitals_today"]
    print(f"  └─ State['patient_intake_context'] populated for {demo['name']} ({demo['age']}{demo['sex'][0]})")

    # Stage 2: Parallel EHR Domain Agents
    print("\n[Stage 2: parallel_ehr_domain_agents (4 Concurrent Specialist Sub-Agents)]")
    print(f"  ├─ [hospitalization_notes_agent]     -> get_hospitalizations_and_clinical_notes('{patient_id}')")
    encounters_data = get_hospitalizations_and_clinical_notes(patient_id)

    print(f"  ├─ [medication_reconciliation_agent] -> get_medication_reconciliation_history('{patient_id}')")
    meds_data = get_medication_reconciliation_history(patient_id)

    print(f"  ├─ [labs_imaging_trend_agent]        -> get_longitudinal_labs_and_imaging('{patient_id}')")
    labs_data = get_longitudinal_labs_and_imaging(patient_id)

    print(f"  └─ [open_loops_care_gaps_agent]      -> get_open_loops_and_care_gaps('{patient_id}')")
    loops_data = get_open_loops_and_care_gaps(patient_id)

    # Stage 3: Chief Medical Synthesizer + Swimlane Graph
    print("\n[Stage 3: pre_chart_brief_synthesizer]")
    print(f"  ├─ Calling tool: generate_clinical_swimlane_graph('{patient_id}')")
    swimlane_data = generate_clinical_swimlane_graph(patient_id)
    print("  └─ Synthesizing State['encounters_summary', 'medication_summary', 'diagnostics_summary', 'open_loops_summary']\n")

    allergies_str = ", ".join(
        f"**{a['substance']}** ({a['reaction']} - {a['severity']})" for a in demo["allergies"]
    )
    problems_str = ", ".join(f"{p['condition']} ({p['icd10']})" for p in demo["active_problem_list"])

    print("=" * 88)
    print(f"# 1-PAGE PHYSICIAN PRE-CHART BRIEF: {demo['name'].upper()} ({demo['patient_id']})")
    print("=" * 88)
    print(f"**Patient:** {demo['name']} ({demo['age']}yo {demo['sex']}, DOB: {demo['dob']}) | **PCP:** {demo['primary_care_physician']}")
    print(f"**Allergies:** {allergies_str}")
    print(f"**Active Problem List:** {problems_str}")
    print(f"**Today's Visit ({visit['visit_date']}):** {visit['appointment_type']}")
    print(f"**Chief Complaint:** *\"{visit['chief_complaint']}\"*")
    print(
        f"**Today's Triage Vitals:** BP **{vitals['bp']}** | HR {vitals['hr']} | "
        f"SpO2 {vitals['spo2']} | Weight **{vitals['weight_lbs']} lbs** (BMI {vitals['bmi']})"
    )
    print(f"**MA Intake Note:** {vitals['ma_intake_note']}\n")

    print("## 1. Interactive Multi-Track Clinical Swimlane Graph (4 Parallel Temporal Tracks)")
    print(f"**Interactive HTML/SVG Swimlane Viewer:** `{swimlane_data['interactive_html_path']}`\n")
    print(swimlane_data["mermaid_swimlane"])
    print()
    print(swimlane_data["markdown_swimlane_matrix"])
    print()

    print("## 2. Recent Hospitalizations, ED Visits & Specialist Notes")
    for enc in encounters_data["encounters_and_notes"]:
        print(f"- **[{enc['date']}] {enc['type']}** ({enc['facility']} — *{enc['author']}*)")
        print(f"  - **Diagnosis:** {enc['primary_diagnosis']}")
        print(f"  - **Key Summary:** {enc['summary_note']}")

    print("\n## 3. Longitudinal Medication Reconciliation & Adherence Alerts")
    print("### Active & Recently Changed Prescriptions")
    for med in meds_data["medications"]["active_prescriptions"]:
        print(
            f"- **{med['medication']}** ({med['prescribed_dose']}) — *{med['change_type']}*\n"
            f"  - **Prior Dose:** {med['previous_dose']} | **Real-World Status:** **{med['actual_patient_adherence']}**"
        )
    if meds_data["medications"]["held_or_discontinued_medications"]:
        print("\n### Held or Discontinued Medications (Re-evaluation Required)")
        for held in meds_data["medications"]["held_or_discontinued_medications"]:
            print(
                f"- **{held['medication']}** ({held['prior_dose']}) — **{held['status']}**\n"
                f"  - **Reason Held:** {held['reason']}\n"
                f"  - **Restart Criteria:** {held['reinitiation_criteria']}"
            )

    print("\n## 4. Longitudinal Lab Trends & Diagnostic Imaging")
    print("| Lab Test | Ref Range | Historical Trajectory (Chronological) |")
    print("| :--- | :--- | :--- |")
    for lab in labs_data["labs_and_diagnostics"]["longitudinal_labs"]:
        traj = " → ".join(
            f"**{h['value']}** [{h['flag']}] ({h['date']}, *{h['context']}*)" for h in lab["history"]
        )
        print(f"| **{lab['test']}** | `{lab['ref_range']}` | {traj} |")

    if labs_data["labs_and_diagnostics"]["imaging_and_procedures"]:
        print("\n### Diagnostic Imaging & Procedures")
        for img in labs_data["labs_and_diagnostics"]["imaging_and_procedures"]:
            print(f"- **[{img['date']}] {img['modality']}:** {img['findings']}")

    print("\n## 5. Unresolved Clinical Issues ('Open Loops') & Action Plan for Today")
    for idx, item in enumerate(loops_data["unresolved_items_and_care_gaps"], start=1):
        print(f"{idx}. **[{item['priority']}] {item['category']}** (`{item['item_id']}`)")
        print(f"   - {item['details']}")
    print("=" * 88 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ADK Longitudinal EHR Chart Summarizer")
    parser.add_argument(
        "--patient",
        default="PAT-1001",
        help="Patient ID or name to summarize (e.g., PAT-1001, PAT-1002, PAT-1003)",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT"),
        help="GCP Project ID for authenticating via GCP SSO / Vertex AI Application Default Credentials",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        help="GCP Vertex AI region (default: global)",
    )
    parser.add_argument(
        "--check-sso",
        action="store_true",
        help="Verify GCP SSO Application Default Credentials (ADC) status and exit",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all patients on today's clinic schedule",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run deterministic local multi-agent pipeline trace without calling external LLM APIs",
    )
    args = parser.parse_args()

    if args.project:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
        os.environ["GOOGLE_CLOUD_LOCATION"] = args.location

    if args.check_sso:
        import warnings
        import google.auth

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            creds, detected_project = google.auth.default()
        effective_project = args.project or detected_project
        print("\n=== GCP SSO / Application Default Credentials (ADC) Status ===")
        print(f"  ADC Credentials Loaded : {creds is not None} ({type(creds).__name__})")
        print(f"  Quota / Default Project: {effective_project or 'Not set (pass --project <PROJECT_ID>)'}")
        print(f"  Vertex AI Location     : {args.location}")
        print(f"  GOOGLE_GENAI_USE_VERTEXAI: {os.environ.get('GOOGLE_GENAI_USE_VERTEXAI', 'FALSE')}\n")
        return

    if args.list:
        schedule = list_scheduled_patients()
        print("\nToday's Clinic Schedule:")
        for p in schedule["patients"]:
            print(f"  - {p['patient_id']}: {p['name']} ({p['age']}{p['sex'][0]}) — {p['chief_complaint']}")
        return

    has_api_creds = bool(
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") and os.environ.get("GOOGLE_CLOUD_PROJECT"))
    )

    if has_api_creds and not args.offline:
        if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
            print(
                f"[GCP SSO / Vertex AI] Connected using Application Default Credentials "
                f"(Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}, "
                f"Location: {os.environ.get('GOOGLE_CLOUD_LOCATION', 'global')})"
            )
        asyncio.run(run_live_adk_pipeline(args.patient))
    else:
        if not args.offline:
            print(
                "[Note] GCP SSO (ADC) is active, but no GCP Project ID is specified yet.\n"
                "  • To run live with GCP SSO (Vertex AI): pass `--project <YOUR_GCP_PROJECT_ID>`\n"
                "    or set `GOOGLE_CLOUD_PROJECT=<YOUR_GCP_PROJECT_ID>`.\n"
                "  • Running deterministic ADK Multi-Agent Pipeline trace below:\n"
            )
        run_deterministic_agentic_pipeline(args.patient)


if __name__ == "__main__":
    main()

