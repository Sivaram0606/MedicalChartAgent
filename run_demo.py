"""
CLI Runner for `ehr_chart_summary_agent` (Google ADK).

Supports:
1. `--list`: Lists all 7 patients currently registered in the Emergency Ward FHIR store (`pat-001`..`pat-007`).
2. Live Google ADK Execution (`InMemoryRunner` with `gemini-3.8-flash` on Vertex AI `global`).
3. `--offline`: Deterministic local multi-agent trace across FHIR compartments, 4-Track Clinical Swimlane
   Graph, and 5-digit ZIP-code outbreak surveillance.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import ssl
from pathlib import Path
import certifi
from dotenv import load_dotenv
from google.genai import types

if not os.environ.get("SSL_CERT_FILE") and ssl.get_default_verify_paths().cafile is None:
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

# Load .env from package or root directory
for candidate_env in (
    Path(__file__).resolve().parent / "ehr_chart_summary_agent" / ".env",
    Path(__file__).resolve().parent / ".env",
):
    if candidate_env.exists():
        load_dotenv(candidate_env, override=True)
        break

try:
    from ehr_chart_summary_agent.agent import chart_review_pipeline
    from ehr_chart_summary_agent.clinical_tools import (
        check_drug_brand_or_generic,
        get_location_outbreak_and_disease_data,
        list_emergency_ward_patients,
    )
    from ehr_chart_summary_agent.ehr_chart_tools import (
        generate_clinical_swimlane_graph,
        get_hospitalizations_and_clinical_notes,
        get_longitudinal_labs_and_imaging,
        get_medication_reconciliation_history,
        get_open_loops_and_care_gaps,
        get_patient_demographics_and_triage,
    )
except ImportError:
    from agent import chart_review_pipeline  # type: ignore
    from clinical_tools import (  # type: ignore
        check_drug_brand_or_generic,
        get_location_outbreak_and_disease_data,
        list_emergency_ward_patients,
    )
    from ehr_chart_tools import (  # type: ignore
        generate_clinical_swimlane_graph,
        get_hospitalizations_and_clinical_notes,
        get_longitudinal_labs_and_imaging,
        get_medication_reconciliation_history,
        get_open_loops_and_care_gaps,
        get_patient_demographics_and_triage,
    )


async def run_live_adk_pipeline(patient_id: str) -> None:
    """Runs the live Google ADK `chart_review_pipeline` using `InMemoryRunner`."""
    from google.adk.runners import InMemoryRunner

    swimlane_info = generate_clinical_swimlane_graph(patient_id)
    runner = InMemoryRunner(
        agent=chart_review_pipeline,
        app_name="ehr_chart_summary_agent",
    )
    session = await runner.session_service.create_session(
        app_name="ehr_chart_summary_agent",
        user_id="ed_attending_physician",
    )

    prompt = (
        f"Generate a complete 1-page longitudinal physician chart brief for patient {patient_id}, "
        f"including medication Original Drug vs. Brand Name verification, OpenFDA adverse effects, "
        f"and the Interactive Multi-Track Clinical Swimlane Graph."
    )
    print(f"\n[ADK Live Runner] Starting `ehr_chart_summary_agent` pipeline for {patient_id}...\n")

    user_msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    final_output = ""
    async for event in runner.run_async(
        user_id="ed_attending_physician",
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
                print(f"  [OK] [{author}] completed stage output.")
                if author == "pre_chart_brief_synthesizer":
                    final_output = text

    if final_output:
        print("\n" + "=" * 92)
        print(final_output)
        print("=" * 92)
    if swimlane_info.get("status") == "success":
        print(f"\n[Interactive 4-Track Clinical Swimlane HTML]: {swimlane_info['interactive_html_path']}\n")


def run_deterministic_trace(patient_id: str) -> None:
    """Executes the FHIR-backed multi-agent tool pipeline deterministically."""
    print("=" * 92)
    print(" GOOGLE ADK EXECUTION TRACE: ehr_chart_summary_agent (HL7 FHIR R4)")
    print("=" * 92)

    intake = get_patient_demographics_and_triage(patient_id)
    if intake.get("status") != "success":
        print(f"Error: {intake.get('message')}")
        return

    canonical_id = intake["patient_id"]
    demo = intake["demographics"]
    visit = intake["todays_visit"]
    vitals = visit.get("triage_vitals_today", {})

    encounters_data = get_hospitalizations_and_clinical_notes(canonical_id)
    meds_data = get_medication_reconciliation_history(canonical_id)
    labs_data = get_longitudinal_labs_and_imaging(canonical_id)
    loops_data = get_open_loops_and_care_gaps(canonical_id)
    swimlane_data = generate_clinical_swimlane_graph(canonical_id)

    print(f"\n# 1-PAGE PHYSICIAN CHART BRIEF: {demo['name'].upper()} ({canonical_id})")
    print(f"**FHIR Source:** {intake['fhir_data_source']} (`Patient/{canonical_id}`)")
    print(f"**Patient:** {demo['name']} ({demo['age']}yo {demo['sex']}, DOB: {demo['dob']}) | **ZIP Code:** `{demo['postal_code']}`")
    print(f"**Today's Chief Complaint:** *\"{visit.get('chief_complaint', '')}\"*")
    print(
        f"**Triage Vitals:** BP **{vitals.get('bp')}** | HR {vitals.get('hr')} | "
        f"SpO2 {vitals.get('spo2')} | Wt **{vitals.get('weight_lbs')} lbs**"
    )
    print(f"**Triage Note:** {vitals.get('ma_intake_note', '')}\n")

    print("## 1. Interactive 4-Track Clinical Swimlane Graph")
    print(f"**HTML Viewer:** `{swimlane_data['interactive_html_path']}`\n")
    print(swimlane_data["mermaid_swimlane"])
    print()
    print(swimlane_data["markdown_swimlane_matrix"])

    print("\n## 2. Medications (FHIR Reconciliation + RxNorm Brand/Generic)")
    for med in meds_data["medications"]["active_prescriptions"]:
        rx = check_drug_brand_or_generic(med["medication"], med.get("rxcui_code", ""))
        print(
            f"- **{med['medication']}** [{rx.get('classification', 'UNKNOWN')}] — `{med['prescribed_dose']}`\n"
            f"  - *Change:* {med['change_type']} | *Adherence:* {med['actual_patient_adherence']}"
        )
    for held in meds_data["medications"]["held_or_discontinued_medications"]:
        print(
            f"- **[HELD/STOPPED] {held['medication']}** — {held['status']}\n"
            f"  - *Reason:* {held['reason']} | *Restart Criteria:* {held['reinitiation_criteria']}"
        )

    print("\n## 3. Longitudinal Lab Trends")
    for lab in labs_data["labs_and_diagnostics"]["longitudinal_labs"]:
        traj = " -> ".join(f"{h['value']} [{h['flag']}] ({h['date']})" for h in lab["history"])
        print(f"- **{lab['test']}** (Ref `{lab['ref_range']}`): {traj}")

    print("\n## 4. Unresolved Open Loops & Safety Alerts")
    for idx, item in enumerate(loops_data["unresolved_items_and_care_gaps"], start=1):
        print(f"{idx}. **[{item['priority']}] {item['category']}**: {item['details']}")

    if demo.get("postal_code"):
        zip_surv = get_location_outbreak_and_disease_data(demo["postal_code"])
        print(f"\n## 5. Hyperlocal ZIP-Code Surveillance ({zip_surv.get('surveillance_granularity')})")
        ed = zip_surv.get("active_outbreaks_in_zip_catchment", {}).get("local_emergency_department_trajectories", {})
        for p in ed.get("pathogen_ed_trajectories", []):
            print(f"- **Local ED {p['pathogen']}**: {p['percent_of_local_ed_visits']}% visits (Trend: {p['weekly_outbreak_trend']})")
    print("=" * 92 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ehr_chart_summary_agent (Google ADK + FHIR R4)")
    parser.add_argument("--patient", default="pat-005", help="Patient ID (pat-001..pat-007) or name")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"))
    parser.add_argument("--list", action="store_true", help="List Emergency Ward patients in FHIR")
    parser.add_argument("--offline", action="store_true", help="Run deterministic local FHIR trace without LLM call")
    args = parser.parse_args()

    if args.project:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
        os.environ["GOOGLE_CLOUD_LOCATION"] = args.location

    if args.list:
        roster = list_emergency_ward_patients()
        print(f"\nEmergency Ward FHIR Roster ({roster['ward_patient_count']} patients — {roster['fhir_data_source']}):")
        for p in roster["patients"]:
            print(f"  - {p['patient_id']}: {p['full_name']} ({p['location']}) — {p['chief_complaint_today']}")
        return

    has_creds = bool(
        os.environ.get("GOOGLE_API_KEY")
        or (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") and os.environ.get("GOOGLE_CLOUD_PROJECT"))
    )
    if has_creds and not args.offline:
        asyncio.run(run_live_adk_pipeline(args.patient))
    else:
        run_deterministic_trace(args.patient)


if __name__ == "__main__":
    main()
