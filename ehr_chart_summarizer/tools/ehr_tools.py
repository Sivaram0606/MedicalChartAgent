"""EHR Compartment Tool Functions for Google ADK Clinical Sub-Agents.

Each tool queries a specific domain of the mock Electronic Health Record (EHR)
database so specialized agents can retrieve structured evidence cleanly.
"""

from typing import Any, Dict
from ..data.mock_ehr_db import MOCK_EHR_DB


def _resolve_patient_id(patient_identifier: str) -> str | None:
    """Resolves a patient ID or partial name to a valid canonical patient_id."""
    query = patient_identifier.strip().upper()
    if query in MOCK_EHR_DB:
        return query
    for pid, record in MOCK_EHR_DB.items():
        name = record["demographics"]["name"].upper()
        if query in name or name in query:
            return pid
    return None


def list_scheduled_patients() -> Dict[str, Any]:
    """Lists all patients on today's clinic schedule with their ID, demographics, and chief complaint.

    Returns:
        dict: A dictionary containing the list of scheduled patients for today.
    """
    patients = []
    for pid, data in MOCK_EHR_DB.items():
        demo = data["demographics"]
        visit = data["todays_visit"]
        patients.append(
            {
                "patient_id": pid,
                "name": demo["name"],
                "age": demo["age"],
                "sex": demo["sex"],
                "appointment_type": visit["appointment_type"],
                "chief_complaint": visit["chief_complaint"],
            }
        )
    return {"status": "success", "scheduled_patients_count": len(patients), "patients": patients}


def get_patient_demographics_and_triage(patient_id: str) -> Dict[str, Any]:
    """Retrieves patient demographics, allergies, active problem list, and today's intake vitals/chief complaint.

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001', 'PAT-1002', 'PAT-1003') or patient name.

    Returns:
        dict: Demographics, allergies, problem list, and today's intake triage data.
    """
    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id:
        return {
            "status": "error",
            "message": f"Patient '{patient_id}' not found. Available IDs: {list(MOCK_EHR_DB.keys())}",
        }
    record = MOCK_EHR_DB[resolved_id]
    return {
        "status": "success",
        "patient_id": resolved_id,
        "demographics": record["demographics"],
        "todays_visit": record["todays_visit"],
    }


def get_hospitalizations_and_clinical_notes(patient_id: str) -> Dict[str, Any]:
    """Retrieves longitudinal hospital discharge summaries, ED visit notes, and specialist consult notes.

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001') or patient name.

    Returns:
        dict: Chronological clinical encounters and unstructured notes.
    """
    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id:
        return {"status": "error", "message": f"Patient '{patient_id}' not found."}
    record = MOCK_EHR_DB[resolved_id]
    return {
        "status": "success",
        "patient_id": resolved_id,
        "patient_name": record["demographics"]["name"],
        "encounters_and_notes": record["encounters_and_notes"],
    }


def get_medication_reconciliation_history(patient_id: str) -> Dict[str, Any]:
    """Retrieves active prescriptions, recent dose changes, held/discontinued medications, and pharmacy adherence notes.

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001') or patient name.

    Returns:
        dict: Active medications, held/discontinued drugs, and adherence/prior-auth status.
    """
    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id:
        return {"status": "error", "message": f"Patient '{patient_id}' not found."}
    record = MOCK_EHR_DB[resolved_id]
    return {
        "status": "success",
        "patient_id": resolved_id,
        "patient_name": record["demographics"]["name"],
        "allergies": record["demographics"]["allergies"],
        "medications": record["medications"],
    }


def get_longitudinal_labs_and_imaging(patient_id: str) -> Dict[str, Any]:
    """Retrieves multi-year laboratory test trends and diagnostic imaging/procedure reports (CT, Echo, etc.).

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001') or patient name.

    Returns:
        dict: Longitudinal lab panels with historical values and imaging reports.
    """
    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id:
        return {"status": "error", "message": f"Patient '{patient_id}' not found."}
    record = MOCK_EHR_DB[resolved_id]
    return {
        "status": "success",
        "patient_id": resolved_id,
        "patient_name": record["demographics"]["name"],
        "labs_and_diagnostics": record["labs_and_diagnostics"],
    }


def get_open_loops_and_care_gaps(patient_id: str) -> Dict[str, Any]:
    """Retrieves unresolved clinical trackers, unreviewed specialty labs, pending imaging follow-ups, and care gaps.

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001') or patient name.

    Returns:
        dict: Open clinical loops, missed appointments, and preventive care gaps.
    """
    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id:
        return {"status": "error", "message": f"Patient '{patient_id}' not found."}
    record = MOCK_EHR_DB[resolved_id]
    return {
        "status": "success",
        "patient_id": resolved_id,
        "patient_name": record["demographics"]["name"],
        "unresolved_items_and_care_gaps": record["unresolved_items_and_care_gaps"],
    }


def generate_clinical_swimlane_graph(patient_id: str) -> Dict[str, Any]:
    """Generates an Interactive Multi-Track Clinical Swimlane Graph synchronizing 4 parallel temporal tracks along a shared horizontal timeline.

    The 4 synchronized tracks are:
      - Track 1: Encounters, Admissions & Consults
      - Track 2: Medication Changes, Held Drugs & Real-World Adherence
      - Track 3: Longitudinal Labs, Vitals & Diagnostic Imaging
      - Track 4: Open Clinical Loops, Care Gaps & Safety Alerts

    Args:
        patient_id: The patient identifier (e.g., 'PAT-1001', 'PAT-1002', 'PAT-1003') or patient name.

    Returns:
        dict: Synchronized 4-track temporal timeline, cross-track causal links, Mermaid swimlane diagram, Markdown horizontal matrix, and path to the interactive HTML/SVG swimlane graph.
    """
    from .swimlane_graph import (
        PATIENT_SWIMLANE_DATA,
        SWIMLANE_TRACKS,
        build_markdown_swimlane_matrix,
        build_mermaid_swimlane,
        generate_interactive_swimlane_html,
    )

    resolved_id = _resolve_patient_id(patient_id)
    if not resolved_id or resolved_id not in PATIENT_SWIMLANE_DATA:
        return {"status": "error", "message": f"Patient '{patient_id}' not found."}

    pdata = PATIENT_SWIMLANE_DATA[resolved_id]
    html_path = generate_interactive_swimlane_html(resolved_id)
    return {
        "status": "success",
        "patient_id": resolved_id,
        "patient_name": pdata["patient_name"],
        "headline": pdata["headline"],
        "tracks": SWIMLANE_TRACKS,
        "synchronized_timepoints": pdata["timepoints"],
        "causal_links": pdata["causal_links"],
        "mermaid_swimlane": build_mermaid_swimlane(resolved_id),
        "markdown_swimlane_matrix": build_markdown_swimlane_matrix(resolved_id),
        "interactive_html_path": html_path,
    }

