"""
FHIR-Backed Longitudinal EHR Compartment Tools (Ported & Unified from MedicalChartAgent).

Replaces `MedicalChartAgent`'s static `mock_ehr_db.py` by pulling all 5 clinical chart
compartments and the 4-Track Interactive Clinical Swimlane Graph directly from HL7 FHIR R4
`Patient/$everything` bundles in the GCP Cloud Healthcare FHIR Store (`synthe_data`), with
automatic fallback to `fhir_cohort_data` FHIR R4 bundles.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from typing import Any

try:
    from .fhir_cohort_data import PATIENT_ID_ALIASES, RAW_COHORT_SPECS, build_fallback_bundles
    from .swimlane_graph import (
        SWIMLANE_TRACKS,
        build_markdown_swimlane_matrix,
        build_mermaid_swimlane,
        extract_swimlane_from_fhir_bundle,
        generate_interactive_swimlane_html,
    )
except ImportError:
    from fhir_cohort_data import PATIENT_ID_ALIASES, RAW_COHORT_SPECS, build_fallback_bundles  # type: ignore
    from swimlane_graph import (  # type: ignore
        SWIMLANE_TRACKS,
        build_markdown_swimlane_matrix,
        build_mermaid_swimlane,
        extract_swimlane_from_fhir_bundle,
        generate_interactive_swimlane_html,
    )

logger = logging.getLogger(__name__)

_SAFE_QUERY_RE = re.compile(r"^[A-Za-z0-9\s._'\-]{1,128}$")
FALLBACK_BUNDLES: dict[str, dict[str, Any]] = build_fallback_bundles()


def resolve_canonical_patient_id(patient_identifier: str) -> str:
    """Resolves a FHIR patient ID (`pat-001`..`pat-007`), legacy ID (`PAT-1001`), or patient name."""
    if not patient_identifier or not _SAFE_QUERY_RE.match(patient_identifier.strip()):
        return ""
    raw = patient_identifier.strip()
    upper = raw.upper()
    if upper in PATIENT_ID_ALIASES:
        return PATIENT_ID_ALIASES[upper]
    lower = raw.lower()
    if lower in FALLBACK_BUNDLES:
        return lower
    for spec in RAW_COHORT_SPECS:
        full_name = f"{' '.join(spec['given'])} {spec['family']}".upper()
        if upper in full_name or full_name in upper:
            return spec["patient_id"]
    return raw


def _fetch_fhir_everything_bundle(patient_identifier: str) -> tuple[str, dict[str, Any] | None, str]:
    """Fetches `Patient/<id>/$everything` from GCP FHIR Store with fallback to local FHIR R4 bundle."""
    pid = resolve_canonical_patient_id(patient_identifier)
    if not pid:
        return "", None, ""

    bundle: dict[str, Any] | None = None
    data_source = "GCP Cloud Healthcare FHIR Store (synthe_data)"
    try:
        try:
            from .server import get_patient_everything
        except ImportError:
            from server import get_patient_everything  # type: ignore

        bundle = get_patient_everything(pid)
    except Exception as exc:
        logger.warning("GCP FHIR $everything lookup failed for %s: %s", pid, type(exc).__name__)

    if not bundle or "entry" not in bundle:
        if pid in FALLBACK_BUNDLES:
            bundle = FALLBACK_BUNDLES[pid]
            data_source = "Synthea FHIR R4 Emergency Ward Clinical Store (synthe_data fallback)"

    return pid, bundle, data_source


def _compute_age(birth_date: str) -> int | None:
    try:
        dob = datetime.strptime(birth_date[:10], "%Y-%m-%d")
        return max(0, 2026 - dob.year - ((11, 13) < (dob.month, dob.day)))
    except Exception:
        return None


def _extract_patient_name(bundle: dict[str, Any]) -> str:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Patient":
            names = res.get("name", [])
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                return f"{given} {family}".strip() or "Unknown"
    return "Unknown"


def get_patient_demographics_and_triage(patient_id: str) -> dict[str, Any]:
    """
    Retrieves patient demographics, residential ZIP code, allergies, active problem list (SNOMED + ICD-10),
    and today's Emergency Ward triage vitals, chief complaint, and MA/nurse intake note from FHIR R4.

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007'), legacy alias ('PAT-1001'), or name.

    Returns:
        Dictionary with structured demographics, allergies, active problem list, today's triage visit, and FHIR citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {
            "status": "error",
            "message": f"Patient '{patient_id}' not found in FHIR store. Available ward IDs: {list(FALLBACK_BUNDLES.keys())}",
        }

    demographics: dict[str, Any] = {}
    allergies: list[dict[str, Any]] = []
    active_problems: list[dict[str, Any]] = []
    todays_visit: dict[str, Any] = {}
    citations: list[dict[str, str]] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        rid = res.get("id", "unknown")

        if rtype == "Patient":
            names = res.get("name", [])
            full_name = (
                f"{' '.join(names[0].get('given', []))} {names[0].get('family', '')}".strip()
                if names
                else "Unknown"
            )
            addrs = res.get("address", [])
            addr = addrs[0] if addrs else {}
            gp = res.get("generalPractitioner", [])
            demographics = {
                "patient_id": pid,
                "name": full_name,
                "dob": res.get("birthDate", "unknown"),
                "age": _compute_age(res.get("birthDate", "")),
                "sex": (res.get("gender") or "unknown").capitalize(),
                "primary_care_physician": gp[0].get("display", "Attending Physician") if gp else "Attending Physician",
                "city": addr.get("city", ""),
                "state": addr.get("state", ""),
                "postal_code": addr.get("postalCode", ""),
                "fhir_resource": f"Patient/{rid}",
            }
            citations.append({"source_name": data_source, "fhir_resource": f"Patient/{rid}"})

        elif rtype == "AllergyIntolerance":
            rxns = res.get("reaction", [])
            manifest = rxns[0].get("manifestation", [{}])[0].get("text", "Not specified") if rxns else "Not specified"
            sev = rxns[0].get("severity", res.get("criticality", "unknown")) if rxns else res.get("criticality", "unknown")
            allergies.append(
                {
                    "substance": res.get("code", {}).get("text", "Unknown"),
                    "reaction": manifest,
                    "severity": str(sev).capitalize(),
                    "criticality": res.get("criticality", "unknown"),
                    "fhir_resource": f"AllergyIntolerance/{rid}",
                }
            )
            citations.append({"source_name": data_source, "fhir_resource": f"AllergyIntolerance/{rid}"})

        elif rtype == "Condition":
            c_status = (res.get("clinicalStatus", {}).get("coding") or [{}])[0].get("code", "")
            if c_status in ("active", "recurrence", "relapse"):
                codings = res.get("code", {}).get("coding", [])
                icd10 = next((c.get("code") for c in codings if "icd-10" in str(c.get("system", ""))), None)
                snomed = next((c.get("code") for c in codings if "snomed" in str(c.get("system", ""))), None)
                active_problems.append(
                    {
                        "condition": res.get("code", {}).get("text") or (codings[0].get("display") if codings else "Condition"),
                        "icd10": icd10,
                        "snomed_code": snomed,
                        "onset": str(res.get("onsetDateTime", ""))[:10],
                        "fhir_resource": f"Condition/{rid}",
                    }
                )
                citations.append({"source_name": data_source, "fhir_resource": f"Condition/{rid}"})

        elif rtype == "Encounter" and res.get("status") == "in-progress":
            vitals_dict: dict[str, Any] = {}
            ma_note = ""
            for ext in res.get("extension", []):
                if ext.get("url", "").endswith("/triage-vitals-json"):
                    try:
                        vitals_dict = json.loads(ext.get("valueString", "{}"))
                    except json.JSONDecodeError:
                        pass
                elif ext.get("url", "").endswith("/ma-intake-note"):
                    ma_note = ext.get("valueString", "")
            todays_visit = {
                "encounter_id": rid,
                "visit_date": str(res.get("period", {}).get("start", ""))[:10],
                "appointment_type": (res.get("type") or [{}])[0].get("text", "Emergency Ward Triage"),
                "chief_complaint": (res.get("reasonCode") or [{}])[0].get("text", ""),
                "triage_vitals_today": {
                    **vitals_dict,
                    "ma_intake_note": ma_note,
                },
                "fhir_resource": f"Encounter/{rid}",
            }
            citations.append({"source_name": data_source, "fhir_resource": f"Encounter/{rid}"})

    demographics["allergies"] = allergies or [{"substance": "No Known Drug Allergies (NKDA)", "reaction": "None", "severity": "None"}]
    demographics["active_problem_list"] = active_problems

    return {
        "status": "success",
        "patient_id": pid,
        "fhir_data_source": data_source,
        "demographics": demographics,
        "todays_visit": todays_visit,
        "citations": citations,
    }


def get_hospitalizations_and_clinical_notes(patient_id: str) -> dict[str, Any]:
    """
    Retrieves longitudinal hospital discharge summaries, prior ED visit notes, and specialist
    consult notes from FHIR `Encounter` and base64-decoded `DocumentReference` resources.

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007') or patient name.

    Returns:
        Dictionary containing chronological encounters, clinical summary notes, and FHIR resource citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {"status": "error", "message": f"Patient '{patient_id}' not found in FHIR store."}

    enc_map: dict[str, dict[str, Any]] = {}
    doc_by_enc: dict[str, tuple[str, str]] = {}
    citations: list[dict[str, str]] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        rid = res.get("id", "unknown")

        if rtype == "Encounter" and res.get("status") != "in-progress":
            enc_map[rid] = res
        elif rtype == "DocumentReference":
            enc_refs = res.get("context", {}).get("encounter", [])
            target_enc = enc_refs[0].get("reference", "").replace("Encounter/", "") if enc_refs else ""
            b64_data = (
                res.get("content", [{}])[0]
                .get("attachment", {})
                .get("data", "")
            )
            decoded_text = ""
            if b64_data:
                try:
                    decoded_text = base64.b64decode(b64_data).decode("utf-8")
                except Exception:
                    decoded_text = ""
            if target_enc:
                doc_by_enc[target_enc] = (rid, decoded_text)

    encounters_and_notes: list[dict[str, Any]] = []
    for eid, enc in enc_map.items():
        doc_id, note_text = doc_by_enc.get(eid, ("", ""))
        participants = enc.get("participant", [])
        author = participants[0].get("individual", {}).get("display", "Attending Clinician") if participants else "Attending Clinician"
        encounters_and_notes.append(
            {
                "encounter_id": eid,
                "document_reference_id": doc_id or None,
                "date": str(enc.get("period", {}).get("start", ""))[:10],
                "type": (enc.get("type") or [{}])[0].get("text", "Clinical Encounter"),
                "facility": enc.get("serviceProvider", {}).get("display", "Hospital Facility"),
                "author": author,
                "primary_diagnosis": (enc.get("reasonCode") or [{}])[0].get("text", ""),
                "summary_note": note_text,
                "fhir_resources": [f"Encounter/{eid}", *([f"DocumentReference/{doc_id}"] if doc_id else [])],
            }
        )
        citations.append({"source_name": data_source, "fhir_resource": f"Encounter/{eid}"})
        if doc_id:
            citations.append({"source_name": data_source, "fhir_resource": f"DocumentReference/{doc_id}"})

    encounters_and_notes.sort(key=lambda x: x["date"], reverse=True)
    return {
        "status": "success",
        "patient_id": pid,
        "patient_name": _extract_patient_name(bundle),
        "fhir_data_source": data_source,
        "encounters_and_notes": encounters_and_notes,
        "citations": citations,
    }


def get_medication_reconciliation_history(patient_id: str) -> dict[str, Any]:
    """
    Retrieves longitudinal medication reconciliation data from FHIR `MedicationRequest` resources,
    including active prescriptions, dose changes, real-world adherence barriers (self-titration,
    Prior Authorization blocks, chelation interactions), and held/stopped drugs with restart criteria.

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007') or patient name.

    Returns:
        Dictionary containing active prescriptions, held/discontinued medications, RxCUI codes, allergies, and FHIR citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {"status": "error", "message": f"Patient '{patient_id}' not found in FHIR store."}

    active_prescriptions: list[dict[str, Any]] = []
    held_or_discontinued: list[dict[str, Any]] = []
    allergies: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        rid = res.get("id", "unknown")

        if rtype == "AllergyIntolerance":
            allergies.append(
                {
                    "substance": res.get("code", {}).get("text", "Unknown"),
                    "criticality": res.get("criticality", "unknown"),
                    "fhir_resource": f"AllergyIntolerance/{rid}",
                }
            )
        elif rtype == "MedicationRequest":
            status = (res.get("status") or "unknown").lower()
            concept = res.get("medicationCodeableConcept", {})
            codings = concept.get("coding", [])
            rxcui = codings[0].get("code") if codings else ""
            med_name = concept.get("text") or (codings[0].get("display") if codings else "Medication")
            dosage = (res.get("dosageInstruction") or [{}])[0].get("text", "Not specified")

            recon_meta: dict[str, Any] = {}
            for ext in res.get("extension", []):
                if ext.get("url", "").endswith("/med-reconciliation-json"):
                    try:
                        recon_meta = json.loads(ext.get("valueString", "{}"))
                    except json.JSONDecodeError:
                        pass

            if status == "active":
                active_prescriptions.append(
                    {
                        "medication_request_id": rid,
                        "medication": med_name,
                        "rxcui_code": rxcui,
                        "prescribed_dose": dosage,
                        "previous_dose": recon_meta.get("prior_dose", "Not specified"),
                        "change_type": recon_meta.get("change_type") or "ACTIVE",
                        "actual_patient_adherence": recon_meta.get("actual_patient_adherence") or "Adherent per EHR",
                        "fhir_resource": f"MedicationRequest/{rid}",
                    }
                )
            else:
                reason = (
                    recon_meta.get("hold_or_stop_reason")
                    or res.get("statusReason", {}).get("text")
                    or "Held or discontinued"
                )
                held_or_discontinued.append(
                    {
                        "medication_request_id": rid,
                        "medication": med_name,
                        "rxcui_code": rxcui,
                        "prior_dose": recon_meta.get("prior_dose") or dosage,
                        "status": f"{status.upper()} ({str(res.get('authoredOn', ''))[:10]})",
                        "reason": reason,
                        "reinitiation_criteria": recon_meta.get("reinitiation_criteria") or "Evaluate clinically",
                        "fhir_resource": f"MedicationRequest/{rid}",
                    }
                )
            citations.append({"source_name": data_source, "fhir_resource": f"MedicationRequest/{rid}"})

    return {
        "status": "success",
        "patient_id": pid,
        "patient_name": _extract_patient_name(bundle),
        "fhir_data_source": data_source,
        "allergies": allergies,
        "medications": {
            "active_prescriptions": active_prescriptions,
            "held_or_discontinued_medications": held_or_discontinued,
        },
        "citations": citations,
    }


def get_longitudinal_labs_and_imaging(patient_id: str) -> dict[str, Any]:
    """
    Retrieves multi-timepoint laboratory biomarker trajectories (`Baseline -> Peak -> Latest`)
    and diagnostic imaging/procedure reports (`TTE`, `CT Chest`, `CT Head`, `CXR`) from FHIR
    `Observation` (`laboratory`) and `DiagnosticReport` resources.

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007') or patient name.

    Returns:
        Dictionary containing grouped chronological lab trajectories, imaging conclusions, and FHIR citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {"status": "error", "message": f"Patient '{patient_id}' not found in FHIR store."}

    grouped_labs: dict[str, dict[str, Any]] = {}
    imaging_reports: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        rid = res.get("id", "unknown")

        if rtype == "Observation":
            cats = res.get("category", [])
            cat_code = (cats[0].get("coding") or [{}])[0].get("code", "") if cats else ""
            if cat_code != "laboratory":
                continue
            test_name = res.get("code", {}).get("text", "Lab Test")
            loinc = (res.get("code", {}).get("coding") or [{}])[0].get("code", "")
            ref_range = (res.get("referenceRange") or [{}])[0].get("text", "See lab standard")
            flag = (res.get("interpretation") or [{}])[0].get("text", "N")
            context = (res.get("note") or [{}])[0].get("text", "")
            dt = str(res.get("effectiveDateTime", ""))[:10]
            val = (
                res["valueQuantity"].get("value")
                if "valueQuantity" in res
                else res.get("valueString", "")
            )

            if test_name not in grouped_labs:
                grouped_labs[test_name] = {
                    "test": test_name,
                    "loinc_code": loinc,
                    "ref_range": ref_range,
                    "history": [],
                }
            grouped_labs[test_name]["history"].append(
                {
                    "observation_id": rid,
                    "date": dt,
                    "value": val,
                    "flag": flag,
                    "context": context,
                    "fhir_resource": f"Observation/{rid}",
                }
            )
            citations.append({"source_name": data_source, "fhir_resource": f"Observation/{rid}"})

        elif rtype == "DiagnosticReport":
            imaging_reports.append(
                {
                    "diagnostic_report_id": rid,
                    "date": str(res.get("effectiveDateTime", ""))[:10],
                    "modality": res.get("code", {}).get("text", "Diagnostic Study"),
                    "findings": res.get("conclusion", ""),
                    "fhir_resource": f"DiagnosticReport/{rid}",
                }
            )
            citations.append({"source_name": data_source, "fhir_resource": f"DiagnosticReport/{rid}"})

    longitudinal_labs = list(grouped_labs.values())
    for lab in longitudinal_labs:
        lab["history"].sort(key=lambda h: h["date"])
    imaging_reports.sort(key=lambda r: r["date"], reverse=True)

    return {
        "status": "success",
        "patient_id": pid,
        "patient_name": _extract_patient_name(bundle),
        "fhir_data_source": data_source,
        "labs_and_diagnostics": {
            "longitudinal_labs": longitudinal_labs,
            "imaging_and_procedures": imaging_reports,
        },
        "citations": citations,
    }


def get_open_loops_and_care_gaps(patient_id: str) -> dict[str, Any]:
    """
    Retrieves unresolved clinical safety alerts, unreviewed diagnostic tests, held medications
    ready for restart, dropped follow-up imaging orders, and care gaps from FHIR `Flag` resources.

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007') or patient name.

    Returns:
        Dictionary containing prioritized open clinical loops and FHIR resource citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {"status": "error", "message": f"Patient '{patient_id}' not found in FHIR store."}

    priority_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    items: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Flag":
            continue
        rid = res.get("id", "unknown")
        meta: dict[str, Any] = {}
        for ext in res.get("extension", []):
            if ext.get("url", "").endswith("/open-loop-json"):
                try:
                    meta = json.loads(ext.get("valueString", "{}"))
                except json.JSONDecodeError:
                    pass

        priority = meta.get("priority", "HIGH")
        items.append(
            {
                "flag_id": rid,
                "item_id": meta.get("item_id", rid),
                "priority": priority,
                "category": meta.get("category") or (res.get("category") or [{}])[0].get("text", "Clinical Alert"),
                "details": meta.get("details") or res.get("code", {}).get("text", ""),
                "fhir_resource": f"Flag/{rid}",
            }
        )
        citations.append({"source_name": data_source, "fhir_resource": f"Flag/{rid}"})

    items.sort(key=lambda x: priority_rank.get(str(x["priority"]).upper(), 9))
    return {
        "status": "success",
        "patient_id": pid,
        "patient_name": _extract_patient_name(bundle),
        "fhir_data_source": data_source,
        "unresolved_items_and_care_gaps": items,
        "citations": citations,
    }


def generate_clinical_swimlane_graph(patient_id: str) -> dict[str, Any]:
    """
    Generates an Interactive Multi-Track Clinical Swimlane Graph directly from the patient's
    HL7 FHIR R4 `$everything` bundle, synchronizing 4 parallel temporal tracks along a shared
    horizontal timeline:
      - Track 1: Encounters, Admissions & Consults
      - Track 2: Medication Changes, Held Drugs & Real-World Adherence
      - Track 3: Longitudinal Labs, Vitals & Diagnostic Imaging
      - Track 4: Open Clinical Loops, Care Gaps & Safety Alerts

    Args:
        patient_id: Patient FHIR ID (e.g., 'pat-001' through 'pat-007') or patient name.

    Returns:
        Dictionary containing the Mermaid swimlane diagram, Markdown 4-track horizontal matrix,
        cross-track causal links, path to the interactive HTML/SVG viewer, and FHIR citations.
    """
    pid, bundle, data_source = _fetch_fhir_everything_bundle(patient_id)
    if not bundle:
        return {"status": "error", "message": f"Patient '{patient_id}' not found in FHIR store."}

    selected_swimlane = extract_swimlane_from_fhir_bundle(bundle)

    # Populate ward tabs in the interactive HTML viewer across all FHIR cohort patients
    all_swimlanes: dict[str, dict[str, Any]] = {pid: selected_swimlane}
    for ward_pid, fb_bundle in FALLBACK_BUNDLES.items():
        if ward_pid not in all_swimlanes:
            all_swimlanes[ward_pid] = extract_swimlane_from_fhir_bundle(fb_bundle)
    all_swimlanes = dict(sorted(all_swimlanes.items(), key=lambda kv: kv[0]))

    html_path = generate_interactive_swimlane_html(pid, all_swimlanes)
    return {
        "status": "success",
        "patient_id": pid,
        "patient_name": selected_swimlane["patient_name"],
        "fhir_data_source": data_source,
        "headline": selected_swimlane["headline"],
        "tracks": SWIMLANE_TRACKS,
        "synchronized_timepoints": selected_swimlane["timepoints"],
        "causal_links": selected_swimlane["causal_links"],
        "mermaid_swimlane": build_mermaid_swimlane(selected_swimlane),
        "markdown_swimlane_matrix": build_markdown_swimlane_matrix(selected_swimlane),
        "interactive_html_path": html_path,
        "citations": [
            {
                "source_name": data_source,
                "fhir_resource": f"Patient/{pid} ($everything 4-Track Temporal Synthesis)",
            }
        ],
    }
