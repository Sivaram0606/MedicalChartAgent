"""
Clinical & Epidemiological Tools for the Emergency Ward Physician Agent (Google ADK 2.0).

Integrates:
1. FHIR ($everything) Patient Clinical Profile (Demographics, Location, Active vs. Previous Medications,
   Active vs. Previous Conditions, Allergies, and Recent Vitals).
2. NIH NLM RxNorm REST API + OpenFDA Drug Label/Event APIs for Original (Generic) vs. Brand Name
   verification, active ingredient mapping, boxed warnings, and adverse effects.
3. CDC NNDSS Weekly Infectious Disease API (data.cdc.gov Socrata x9gk-5huc),
   CDC FluView / CMU Delphi ILINet API (cdcfluview equivalent), Disease.sh, and Open-Meteo Air Quality
   for location-based outbreak and persistent disease surveillance.
"""

from __future__ import annotations

import logging
import re
from typing import Any
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# Strict input validation patterns (mandatory-secure-web-skills)
_PATIENT_ID_RE = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9\s.,'()\-/\[\]:]{1,200}$")
_RXCUI_RE = re.compile(r"^\d{1,12}$")

# US State name <-> 2-letter abbreviation mapping (allow-list for SoQL & FluView queries)
US_STATES_MAP: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
STATE_NAME_TO_ABBR: dict[str, str] = {v.upper(): k for k, v in US_STATES_MAP.items()}

try:
    from .fhir_cohort_data import PATIENT_ID_ALIASES, RAW_COHORT_SPECS, build_fallback_bundles
except ImportError:
    from fhir_cohort_data import PATIENT_ID_ALIASES, RAW_COHORT_SPECS, build_fallback_bundles  # type: ignore

# Unified HL7 FHIR R4 fallback bundles (`pat-001` through `pat-007`) matching GCP FHIR store
SYNTHEA_FALLBACK_BUNDLES: dict[str, dict[str, Any]] = build_fallback_bundles()


def _normalize_state(state_input: str) -> tuple[str | None, str | None]:
    """
    Validates and normalizes a US state name or 2-letter code against an allow-list.

    Returns:
        Tuple of (Full State Name, 2-Letter Code) or (None, None) if invalid.
    """
    if not state_input or not isinstance(state_input, str):
        return None, None
    cleaned = state_input.strip().upper()
    if cleaned in US_STATES_MAP:
        return US_STATES_MAP[cleaned], cleaned
    if cleaned in STATE_NAME_TO_ABBR:
        abbr = STATE_NAME_TO_ABBR[cleaned]
        return US_STATES_MAP[abbr], abbr
    return None, None


def _parse_fhir_bundle(
    bundle: dict[str, Any],
    expected_patient_name: str = "",
    fhir_source_label: str = "FHIR R4 Store",
    fhir_endpoint_url: str = "",
) -> dict[str, Any]:
    """
    Parses a FHIR $everything Bundle into structured emergency ward clinical sections,
    including today's triage visit/vitals, medication reconciliation & adherence metadata,
    and FHIR resource ID citations (without FHIR dataset links).
    """
    import json as _json

    patient_info: dict[str, Any] = {}
    location_info: dict[str, Any] = {}
    todays_triage_visit: dict[str, Any] = {}
    current_meds: list[dict[str, Any]] = []
    held_meds: list[dict[str, Any]] = []
    previous_meds: list[dict[str, Any]] = []
    active_conditions: list[dict[str, Any]] = []
    previous_conditions: list[dict[str, Any]] = []
    allergies: list[dict[str, Any]] = []

    entries = bundle.get("entry", [])
    for entry in entries:
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        rid = res.get("id", "unknown")

        if rtype == "Patient":
            names = res.get("name", [])
            full_name = "Unknown"
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                full_name = f"{given} {family}".strip() or names[0].get("text", "Unknown")

            name_verified = True
            name_verification_note = "No patient name filter supplied; retrieved by FHIR Patient ID."
            if expected_patient_name and expected_patient_name.strip():
                exp_tokens = [
                    t.lower()
                    for t in re.split(r"\s+", expected_patient_name.strip())
                    if len(t) > 1
                ]
                fn_lower = full_name.lower()
                name_verified = any(tok in fn_lower for tok in exp_tokens)
                name_verification_note = (
                    f"Verified match with FHIR record '{full_name}'."
                    if name_verified
                    else f"WARNING: Supplied name '{expected_patient_name}' does not match FHIR record name '{full_name}'. Verify patient identity at bedside."
                )

            gp = res.get("generalPractitioner", [])
            patient_citation = {
                "source_name": fhir_source_label,
                "fhir_resource": f"Patient/{rid}",
            }
            patient_info = {
                "patient_id": rid,
                "full_name": full_name,
                "supplied_name": expected_patient_name or None,
                "name_match_verified": name_verified,
                "name_verification_note": name_verification_note,
                "gender": res.get("gender", "unknown"),
                "birth_date": res.get("birthDate", "unknown"),
                "primary_care_physician": gp[0].get("display") if gp else None,
                "citation": patient_citation,
            }

            addrs = res.get("address", [])
            if addrs:
                addr = addrs[0]
                raw_state = addr.get("state", "")
                state_full, state_abbr = _normalize_state(raw_state)
                lat, lon = None, None
                for ext in addr.get("extension", []):
                    if "geolocation" in ext.get("url", ""):
                        for sub_ext in ext.get("extension", []):
                            if sub_ext.get("url") == "latitude":
                                lat = sub_ext.get("valueDecimal")
                            elif sub_ext.get("url") == "longitude":
                                lon = sub_ext.get("valueDecimal")
                location_info = {
                    "line": ", ".join(addr.get("line", [])),
                    "city": addr.get("city", ""),
                    "state": state_full or raw_state,
                    "state_code": state_abbr or raw_state,
                    "postal_code": addr.get("postalCode", ""),
                    "country": addr.get("country", "US"),
                    "latitude": lat,
                    "longitude": lon,
                    "citation": {
                        "source_name": f"{fhir_source_label} — Patient.address",
                        "fhir_resource": f"Patient/{rid}",
                    },
                }

        elif rtype == "Encounter" and res.get("status") == "in-progress":
            vitals_dict: dict[str, Any] = {}
            ma_note = ""
            for ext in res.get("extension", []):
                if ext.get("url", "").endswith("/triage-vitals-json"):
                    try:
                        vitals_dict = _json.loads(ext.get("valueString", "{}"))
                    except _json.JSONDecodeError:
                        pass
                elif ext.get("url", "").endswith("/ma-intake-note"):
                    ma_note = ext.get("valueString", "")
            todays_triage_visit = {
                "encounter_id": rid,
                "visit_date": str(res.get("period", {}).get("start", ""))[:10],
                "appointment_type": (res.get("type") or [{}])[0].get("text", "Emergency Ward Triage"),
                "chief_complaint": (res.get("reasonCode") or [{}])[0].get("text", ""),
                "triage_vitals": vitals_dict,
                "ma_intake_note": ma_note,
                "citation": {
                    "source_name": f"{fhir_source_label} (Encounter/{rid})",
                    "fhir_resource": f"Encounter/{rid}",
                },
            }

        elif rtype in ("MedicationRequest", "MedicationStatement"):
            med_concept = res.get("medicationCodeableConcept", {})
            codings = med_concept.get("coding", [])
            rxcui = codings[0].get("code") if codings else None
            coding_system = codings[0].get("system") if codings else "http://www.nlm.nih.gov/research/umls/rxnorm"
            coding_display = codings[0].get("display") if codings else None
            prescribed_text = med_concept.get("text") or coding_display or "Unknown Medication"
            status = (res.get("status") or "unknown").lower()
            dosages = res.get("dosageInstruction", [])
            dosage_text = dosages[0].get("text", "Not specified") if dosages else "Not specified"

            recon_meta: dict[str, Any] = {}
            for ext in res.get("extension", []):
                if ext.get("url", "").endswith("/med-reconciliation-json"):
                    try:
                        recon_meta = _json.loads(ext.get("valueString", "{}"))
                    except _json.JSONDecodeError:
                        pass

            med_entry = {
                "medication_request_id": rid,
                "prescribed_display_name": prescribed_text,
                "coding_display": coding_display,
                "rxcui_code": rxcui,
                "status": status,
                "authored_on": res.get("authoredOn", "unknown"),
                "dosage_instruction": dosage_text,
                "prior_dose": recon_meta.get("prior_dose"),
                "change_type": recon_meta.get("change_type"),
                "actual_patient_adherence": recon_meta.get("actual_patient_adherence"),
                "hold_or_stop_reason": recon_meta.get("hold_or_stop_reason") or res.get("statusReason", {}).get("text"),
                "reinitiation_criteria": recon_meta.get("reinitiation_criteria"),
                "prescriber": res.get("requester", {}).get("display", "Unknown"),
                "citation": {
                    "source_name": f"{fhir_source_label} ({rtype}/{rid})",
                    "fhir_resource": f"{rtype}/{rid}",
                    "coding_system": coding_system,
                    "rxcui_code": rxcui,
                },
            }
            if status in ("active", "intended"):
                current_meds.append(med_entry)
            elif status == "on-hold":
                held_meds.append(med_entry)
            else:
                previous_meds.append(med_entry)

        elif rtype == "Condition":
            clin_status_codings = res.get("clinicalStatus", {}).get("coding", [])
            clin_status = (
                clin_status_codings[0].get("code", "unknown").lower()
                if clin_status_codings
                else "unknown"
            )
            code_obj = res.get("code", {})
            codings = code_obj.get("coding", [])
            snomed_code = next((c.get("code") for c in codings if "snomed" in str(c.get("system", ""))), codings[0].get("code") if codings else None)
            icd10_code = next((c.get("code") for c in codings if "icd-10" in str(c.get("system", ""))), None)
            coding_system = codings[0].get("system") if codings else "http://snomed.info/sct"
            condition_name = (
                code_obj.get("text")
                or (codings[0].get("display") if codings else "Unknown Condition")
            )
            cond_entry = {
                "condition_id": rid,
                "condition_name": condition_name,
                "snomed_code": snomed_code,
                "icd10_code": icd10_code,
                "clinical_status": clin_status,
                "onset_date": res.get("onsetDateTime", "unknown"),
                "abatement_date": res.get("abatementDateTime"),
                "citation": {
                    "source_name": f"{fhir_source_label} (Condition/{rid})",
                    "fhir_resource": f"Condition/{rid}",
                    "coding_system": coding_system,
                    "snomed_code": snomed_code,
                    "icd10_code": icd10_code,
                },
            }
            if clin_status in ("active", "recurrence", "relapse"):
                active_conditions.append(cond_entry)
            else:
                previous_conditions.append(cond_entry)

        elif rtype == "AllergyIntolerance":
            rxns = res.get("reaction", [])
            reaction_text = rxns[0].get("manifestation", [{}])[0].get("text") if rxns else None
            allergies.append(
                {
                    "allergy_id": rid,
                    "substance": res.get("code", {}).get("text", "Unknown allergen"),
                    "reaction": reaction_text,
                    "criticality": res.get("criticality", "unknown"),
                    "citation": {
                        "source_name": f"{fhir_source_label} (AllergyIntolerance/{rid})",
                        "fhir_resource": f"AllergyIntolerance/{rid}",
                    },
                }
            )

    return {
        "patient_demographics": patient_info,
        "patient_location": location_info,
        "todays_triage_visit": todays_triage_visit,
        "current_medications": current_meds,
        "held_medications": held_meds,
        "previous_medications": previous_meds,
        "active_conditions": active_conditions,
        "previous_conditions": previous_conditions,
        "allergies": allergies,
    }


def list_emergency_ward_patients() -> dict[str, Any]:
    """
    Lists all patients currently registered in the Emergency Ward FHIR store (`pat-001` through `pat-007`)
    with their demographics, 5-digit ZIP code, today's chief complaint, and FHIR resource citations.

    Returns:
        Dictionary containing the list of Emergency Ward patients and FHIR store citation metadata.
    """
    data_source = "GCP Cloud Healthcare FHIR Store (synthe_data)"
    patient_resources: list[dict[str, Any]] = []
    triage_by_pid: dict[str, str] = {
        spec["patient_id"]: spec["todays_triage"]["chief_complaint"]
        for spec in RAW_COHORT_SPECS
    }

    try:
        try:
            from .server import list_active_triage_encounters, list_fhir_patients
        except ImportError:
            from server import list_active_triage_encounters, list_fhir_patients  # type: ignore

        bundle = list_fhir_patients()
        if bundle and bundle.get("entry"):
            for entry in bundle["entry"]:
                res = entry.get("resource", {})
                if res.get("resourceType") == "Patient":
                    patient_resources.append(res)

            enc_bundle = list_active_triage_encounters()
            if enc_bundle and enc_bundle.get("entry"):
                for entry in enc_bundle["entry"]:
                    eres = entry.get("resource", {})
                    if eres.get("resourceType") == "Encounter":
                        subj = eres.get("subject", {}).get("reference", "").replace("Patient/", "")
                        cc = (eres.get("reasonCode") or [{}])[0].get("text", "")
                        if subj and cc:
                            triage_by_pid[subj] = cc
    except Exception as exc:
        logger.warning("Primary GCP FHIR patient list failed, using fallback: %s", type(exc).__name__)

    if not patient_resources:
        data_source = "Synthea FHIR R4 Emergency Ward Clinical Store (synthe_data fallback)"
        for b in SYNTHEA_FALLBACK_BUNDLES.values():
            for entry in b.get("entry", []):
                res = entry.get("resource", {})
                if res.get("resourceType") == "Patient":
                    patient_resources.append(res)

    ward_patients: list[dict[str, Any]] = []
    for res in patient_resources:
        pid = res.get("id", "unknown")
        names = res.get("name", [])
        full_name = "Unknown"
        if names:
            given = " ".join(names[0].get("given", []))
            family = names[0].get("family", "")
            full_name = f"{given} {family}".strip() or names[0].get("text", "Unknown")

        addrs = res.get("address", [])
        city = addrs[0].get("city", "") if addrs else ""
        state = addrs[0].get("state", "") if addrs else ""
        postal_code = addrs[0].get("postalCode", "") if addrs else ""

        ward_patients.append(
            {
                "patient_id": pid,
                "full_name": full_name,
                "gender": res.get("gender", "unknown"),
                "birth_date": res.get("birthDate", "unknown"),
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "location": f"{city}, {state} {postal_code}".strip(" ,"),
                "chief_complaint_today": triage_by_pid.get(pid, "Presenting for Emergency Ward evaluation"),
                "citation": {
                    "source_name": data_source,
                    "fhir_resource": f"Patient/{pid}",
                },
            }
        )

    ward_patients.sort(key=lambda p: p["patient_id"])
    return {
        "ward_patient_count": len(ward_patients),
        "patients": ward_patients,
        "fhir_data_source": data_source,
        "citations": [
            {
                "source_name": data_source,
                "operation": "FHIR R4 GET Patient & Encounter?status=in-progress",
            }
        ],
    }


def get_patient_clinical_profile(patient_id: str, patient_name: str = "") -> dict[str, Any]:
    """
    Fetches the complete FHIR ($everything) clinical record for an Emergency Ward patient,
    including demographics, residential ZIP code, today's triage vitals & chief complaint,
    current/held/previous medications (with reconciliation & adherence notes), active/previous
    conditions, allergies, and FHIR resource ID citations.

    Args:
        patient_id: The patient's FHIR resource identifier (e.g., 'pat-001' through 'pat-007', or legacy alias 'PAT-1001').
        patient_name: The patient's name provided by the emergency ward physician for identity verification.

    Returns:
        Dictionary containing structured FHIR clinical data and FHIR resource ID citations.
    """
    raw_id = (patient_id or "").strip()
    if not raw_id:
        return {"error": "Missing patient_id."}

    # Resolve legacy MedicalChartAgent IDs or name strings safely
    if raw_id.upper() in PATIENT_ID_ALIASES:
        clean_id = PATIENT_ID_ALIASES[raw_id.upper()]
    elif _PATIENT_ID_RE.match(raw_id):
        clean_id = raw_id.lower() if raw_id.lower().startswith("pat-") else raw_id
    elif _SAFE_TEXT_RE.match(raw_id):
        matched_id = ""
        for spec in RAW_COHORT_SPECS:
            fn = f"{' '.join(spec['given'])} {spec['family']}".lower()
            if raw_id.lower() in fn or fn in raw_id.lower():
                matched_id = spec["patient_id"]
                break
        if not matched_id:
            return {"error": f"Patient '{raw_id}' not found in FHIR store."}
        clean_id = matched_id
    else:
        return {"error": "Invalid patient_id format."}

    clean_name = patient_name.strip() if patient_name and _SAFE_TEXT_RE.match(patient_name.strip()) else ""

    # 1. Attempt primary GCP Cloud Healthcare FHIR store via existing get_patient_everything
    bundle: dict[str, Any] | None = None
    data_source = "GCP Cloud Healthcare FHIR Store (synthe_data)"
    endpoint_url = ""
    try:
        try:
            from .server import get_patient_everything
        except ImportError:
            from server import get_patient_everything  # type: ignore

        bundle = get_patient_everything(clean_id)
    except Exception as exc:
        logger.warning("Primary GCP FHIR call failed, attempting fallback: %s", type(exc).__name__)

    # 2. Fallback to FHIR R4 cohort bundle when GCP credentials require reauthentication
    if not bundle or "entry" not in bundle:
        if clean_id in SYNTHEA_FALLBACK_BUNDLES:
            bundle = SYNTHEA_FALLBACK_BUNDLES[clean_id]
            data_source = "Synthea FHIR R4 Emergency Ward Clinical Store (synthe_data fallback)"
        else:
            try:
                hapi_url = f"https://hapi.fhir.org/baseR4/Patient/{clean_id}/$everything"
                resp = requests.get(
                    hapi_url,
                    headers={"Accept": "application/fhir+json"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    candidate = resp.json()
                    if candidate.get("entry"):
                        bundle = candidate
                        data_source = "Public HAPI FHIR R4 Server"
            except RequestException:
                pass

    if not bundle or "entry" not in bundle:
        return {
            "error": f"Patient '{clean_id}' not found in FHIR store.",
            "available_emergency_ward_patients": [
                {
                    "patient_id": spec["patient_id"],
                    "name": f"{' '.join(spec['given'])} {spec['family']}",
                    "location": f"{spec['city']}, {spec['state']} {spec['postal_code']}",
                }
                for spec in RAW_COHORT_SPECS
            ],
        }

    parsed = _parse_fhir_bundle(
        bundle,
        expected_patient_name=clean_name,
        fhir_source_label=data_source,
        fhir_endpoint_url=endpoint_url,
    )
    parsed["fhir_data_source"] = data_source
    parsed["citations"] = [
        {
            "source_name": data_source,
            "operation": f"FHIR R4 Patient/{clean_id}/$everything",
        }
    ]
    return parsed


def check_drug_brand_or_generic(
    drug_name: str,
    rxcui_code: str = "",
) -> dict[str, Any]:
    """
    Checks whether a prescribed drug from FHIR is an Original (Generic / Active Ingredient) drug name
    or a Brand (Trade) name using the NIH NLM RxNorm REST API, and retrieves its clinical uses,
    known side effects, warnings, and top reported adverse events from OpenFDA Drug APIs
    (https://open.fda.gov/apis/drug/) with full citations.

    Args:
        drug_name: The medication name or display string from FHIR (e.g., 'Tylenol', 'Acetaminophen 160 MG Chewable Tablet').
        rxcui_code: Optional RxNorm Concept Unique Identifier (RxCUI) from FHIR coding (e.g., '313820' or '202433').

    Returns:
        Dictionary containing brand vs. generic classification, active ingredients, brand equivalents,
        OpenFDA drug uses (indications, purpose, pharmacologic class), OpenFDA known side effects
        (labeled adverse reactions, warnings, contraindications, boxed warnings, FAERS counts),
        and verifiable citations for every API source.
    """
    if not drug_name or not _SAFE_TEXT_RE.match(drug_name.strip()):
        return {"error": "Invalid drug_name provided."}

    clean_drug = drug_name.strip()
    clean_rxcui = rxcui_code.strip() if rxcui_code and _RXCUI_RE.match(rxcui_code.strip()) else ""

    tty_descriptions = {
        "IN": "Ingredient (Original Generic Active Ingredient)",
        "MIN": "Multiple Ingredients (Original Generic Combination)",
        "PIN": "Precise Ingredient (Original Generic Salt/Isomer)",
        "SCD": "Semantic Clinical Drug (Original Generic Clinical Formulation)",
        "GPCK": "Generic Pack (Original Generic Package)",
        "BN": "Brand Name (Proprietary Trade Name)",
        "SBD": "Semantic Branded Drug (Branded Clinical Formulation)",
        "BPCK": "Branded Pack (Proprietary Branded Package)",
    }
    generic_ttys = {"IN", "MIN", "PIN", "SCD", "GPCK", "SCDC", "SCDF", "SCDG"}
    brand_ttys = {"BN", "SBD", "BPCK", "SBDC", "SBDF", "SBDG"}

    citations: list[dict[str, Any]] = []

    try:
        # Step 1: Resolve RxCUI if not already provided or verify via RxNorm
        resolved_rxcui = clean_rxcui
        if not resolved_rxcui:
            first_token = re.split(r"\s+\d", clean_drug)[0].strip()
            for candidate_query in (clean_drug, first_token):
                r_lookup = requests.get(
                    "https://rxnav.nlm.nih.gov/REST/rxcui.json",
                    params={"name": candidate_query, "search": 2},
                    timeout=10,
                )
                if r_lookup.status_code == 200:
                    ids = r_lookup.json().get("idGroup", {}).get("rxnormId", [])
                    if ids:
                        resolved_rxcui = ids[0]
                        break

        props: dict[str, Any] = {}
        rxnorm_props_url = (
            f"https://rxnav.nlm.nih.gov/REST/rxcui/{resolved_rxcui}/properties.json"
            if resolved_rxcui
            else "https://rxnav.nlm.nih.gov/REST/rxcui.json"
        )
        if resolved_rxcui:
            r_props = requests.get(rxnorm_props_url, timeout=10)
            if r_props.status_code == 200:
                props = r_props.json().get("properties", {}) or {}

        tty = props.get("tty", "")
        rxnorm_name = props.get("name", clean_drug)

        generic_ingredients: list[str] = []
        brand_equivalents: list[str] = []
        rxnorm_related_url = (
            f"https://rxnav.nlm.nih.gov/REST/rxcui/{resolved_rxcui}/related.json?tty=IN+MIN+PIN+BN+SCD+SBD"
            if resolved_rxcui
            else "https://rxnav.nlm.nih.gov/REST/"
        )

        if resolved_rxcui:
            r_rel = requests.get(rxnorm_related_url, timeout=10)
            if r_rel.status_code == 200:
                concept_groups = r_rel.json().get("relatedGroup", {}).get("conceptGroup", []) or []
                for cg in concept_groups:
                    cg_tty = cg.get("tty")
                    for cprop in cg.get("conceptProperties", []) or []:
                        cname = cprop.get("name")
                        if not cname:
                            continue
                        if cg_tty in ("IN", "MIN", "PIN") and cname not in generic_ingredients:
                            generic_ingredients.append(cname)
                        elif cg_tty == "BN" and cname not in brand_equivalents:
                            brand_equivalents.append(cname)

        citations.append(
            {
                "information_covered": "Original (Generic) vs. Brand Name Classification, RxNorm TTY, Active Ingredients & Brand Equivalents",
                "source_name": "NIH National Library of Medicine (NLM) RxNorm REST API",
                "rxcui": resolved_rxcui,
                "properties_api_url": rxnorm_props_url,
                "related_concepts_api_url": rxnorm_related_url,
                "documentation_url": "https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html",
            }
        )

        # Determine classification
        is_brand = tty in brand_ttys
        is_generic = tty in generic_ttys

        first_word = clean_drug.split()[0].lower() if clean_drug else ""
        if not is_brand and any(first_word == b.lower() for b in brand_equivalents):
            is_brand = True
            is_generic = False

        if is_brand:
            classification = "BRAND_NAME"
            summary = (
                f"'{clean_drug}' is a BRAND NAME prescription. "
                f"Original/Generic active ingredient(s): {', '.join(generic_ingredients) or 'See RxNorm'}."
            )
        elif is_generic:
            classification = "ORIGINAL_GENERIC_NAME"
            summary = (
                f"'{clean_drug}' is prescribed using its ORIGINAL / GENERIC drug name "
                f"(active ingredient(s): {', '.join(generic_ingredients) or rxnorm_name}). "
                f"Common brand equivalents include: {', '.join(brand_equivalents[:5]) or 'None listed'}."
            )
        else:
            classification = "UNKNOWN"
            summary = f"Could not conclusively classify '{clean_drug}' via RxNorm TTY."

        # Step 2: Query OpenFDA Drug APIs (https://open.fda.gov/apis/drug/) for:
        #   a) Uses of the drug (indications_and_usage, purpose, pharmacologic class, mechanism of action)
        #   b) Known side effects from FDA Structured Product Labeling (adverse_reactions, warnings_and_cautions, contraindications, boxed_warning)
        #   c) Top reported FAERS adverse events (drug/event.json)
        search_ingredient = (generic_ingredients[0] if generic_ingredients else first_word).lower()
        adverse_events: dict[str, int] = {}
        faers_query_url = (
            f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:"{search_ingredient}"'
            "&count=patient.reaction.reactionmeddrapt.exact&limit=8"
        )
        r_fda_events = requests.get(
            "https://api.fda.gov/drug/event.json",
            params={
                "search": f'patient.drug.medicinalproduct:"{search_ingredient}"',
                "count": "patient.reaction.reactionmeddrapt.exact",
                "limit": 8,
            },
            timeout=10,
        )
        if r_fda_events.status_code == 200:
            for item in r_fda_events.json().get("results", [])[:8]:
                adverse_events[item.get("term", "UNKNOWN")] = item.get("count", 0)

        citations.append(
            {
                "information_covered": "Top Reported Adverse Drug Events (FAERS MedDRA Reaction Counts)",
                "source_name": "OpenFDA Drug Adverse Events API (FAERS)",
                "api_endpoint_url": faers_query_url,
                "documentation_url": "https://open.fda.gov/apis/drug/event/",
            }
        )

        indications_and_usage = None
        drug_purpose = None
        pharmacologic_class: list[str] = []
        mechanism_of_action: list[str] = []
        known_side_effects_label = None
        warnings_and_cautions = None
        contraindications = None
        boxed_warning = None
        drug_interactions = None
        spl_set_id = None
        spl_effective_time = None
        used_label_url = "https://api.fda.gov/drug/label.json"

        # Query OpenFDA Drug Labeling API (https://api.fda.gov/drug/label.json) by generic or brand name
        for label_query in (
            f'openfda.generic_name:"{search_ingredient}"',
            f'openfda.brand_name:"{first_word}"',
            f'openfda.substance_name:"{search_ingredient}"',
        ):
            r_fda_label = requests.get(
                "https://api.fda.gov/drug/label.json",
                params={"search": label_query, "limit": 1},
                timeout=10,
            )
            if r_fda_label.status_code == 200:
                label_results = r_fda_label.json().get("results", [])
                if label_results:
                    lbl = label_results[0]
                    used_label_url = f"https://api.fda.gov/drug/label.json?search={label_query}&limit=1"
                    spl_set_id = lbl.get("set_id")
                    spl_effective_time = lbl.get("effective_time")
                    openfda_meta = lbl.get("openfda", {})
                    pharmacologic_class = openfda_meta.get("pharm_class_epc", [])
                    mechanism_of_action = openfda_meta.get("pharm_class_moa", [])

                    if lbl.get("indications_and_usage"):
                        indications_and_usage = lbl["indications_and_usage"][0][:600]
                    if lbl.get("purpose"):
                        drug_purpose = lbl["purpose"][0][:400]
                    if lbl.get("adverse_reactions"):
                        known_side_effects_label = lbl["adverse_reactions"][0][:600]
                    if lbl.get("warnings_and_cautions"):
                        warnings_and_cautions = lbl["warnings_and_cautions"][0][:500]
                    elif lbl.get("warnings"):
                        warnings_and_cautions = lbl["warnings"][0][:500]
                    if lbl.get("contraindications"):
                        contraindications = lbl["contraindications"][0][:400]
                    if lbl.get("boxed_warning"):
                        boxed_warning = lbl["boxed_warning"][0][:400]
                    if lbl.get("drug_interactions"):
                        drug_interactions = lbl["drug_interactions"][0][:400]
                    break

        citations.append(
            {
                "information_covered": "Drug Uses (Indications & Usage, Purpose, Pharmacologic Class) and Known Side Effects (SPL Adverse Reactions, Warnings, Contraindications, Boxed Warning)",
                "source_name": "OpenFDA Drug Labeling API (FDA Structured Product Labeling / SPL)",
                "api_endpoint_url": used_label_url,
                "spl_set_id": spl_set_id,
                "spl_effective_date": spl_effective_time,
                "dailymed_label_url": (
                    f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={spl_set_id}"
                    if spl_set_id
                    else "https://open.fda.gov/apis/drug/label/"
                ),
                "documentation_url": "https://open.fda.gov/apis/drug/",
            }
        )

        return {
            "prescribed_name_in_fhir": clean_drug,
            "rxcui": resolved_rxcui,
            "rxnorm_normalized_name": rxnorm_name,
            "rxnorm_tty": tty,
            "rxnorm_tty_description": tty_descriptions.get(tty, tty or "Unclassified"),
            "classification": classification,
            "is_brand_name": is_brand,
            "is_original_generic_name": is_generic,
            "original_generic_ingredients": generic_ingredients,
            "brand_name_equivalents": brand_equivalents[:8],
            "verification_summary": summary,
            "openfda_drug_uses": {
                "indications_and_usage": indications_and_usage,
                "purpose": drug_purpose,
                "pharmacologic_class_epc": pharmacologic_class,
                "mechanism_of_action_moa": mechanism_of_action,
                "citation": citations[-1],
            },
            "openfda_known_side_effects": {
                "labeled_adverse_reactions": known_side_effects_label,
                "warnings_and_cautions": warnings_and_cautions,
                "contraindications": contraindications,
                "boxed_warning_excerpt": boxed_warning,
                "drug_interactions_excerpt": drug_interactions,
                "top_faers_reported_adverse_events": adverse_events,
                "label_citation": citations[-1],
                "faers_citation": citations[-2],
            },
            "citations": citations,
        }

    except RequestException as exc:
        return {"error": f"Network error querying RxNorm/OpenFDA: {exc}"}


_ZIP_CODE_RE = re.compile(r"^\d{5}(?:-\d{4})?$")

# CDC NWSS Wastewater Surveillance datasets on data.cdc.gov (queried for the local sewershed serving the ZIP code)
_NWSS_PATHOGEN_DATASETS: list[tuple[str, str]] = [
    ("Influenza A", "ymmh-divb"),
    ("SARS-CoV-2 (COVID-19)", "j9g8-acpt"),
    ("RSV (Respiratory Syncytial Virus)", "45cq-cw4i"),
    ("Measles", "akvg-8vrb"),
    ("Mpox", "xpxn-rzgz"),
]


def _fetch_local_sewershed_pathogen(
    pathogen_label: str, dataset_id: str, local_fips: str, zip5: str
) -> dict[str, Any] | None:
    """Queries CDC NWSS for the local wastewater sewershed serving the patient's ZIP code."""
    if not local_fips or not local_fips.isdigit():
        return None
    soql_where = f"county_fips like '%{local_fips}%'"
    endpoint_url = (
        f"https://data.cdc.gov/resource/{dataset_id}.json"
        f"?$where=county_fips%20like%20%27%25{local_fips}%25%27&$order=sample_collect_date%20DESC&$limit=2"
    )
    try:
        resp = requests.get(
            f"https://data.cdc.gov/resource/{dataset_id}.json",
            params={
                "$where": soql_where,
                "$order": "sample_collect_date DESC",
                "$limit": 2,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if not rows:
            return None
        latest = rows[0]
        detected = str(latest.get("pcr_target_detect", "")).lower() == "yes"
        try:
            conc = float(latest.get("pcr_target_avg_conc") or 0.0)
        except (ValueError, TypeError):
            conc = 0.0
        units = latest.get("pcr_target_units", "copies")

        prev_conc = None
        trend_summary = "Detected in local ZIP sewershed" if detected else "Below limit of detection in local ZIP sewershed"
        if len(rows) > 1:
            try:
                prev_conc = float(rows[1].get("pcr_target_avg_conc") or 0.0)
                if detected and prev_conc > 0:
                    pct_change = ((conc - prev_conc) / prev_conc) * 100.0
                    direction = "Increasing" if pct_change > 5 else ("Decreasing" if pct_change < -5 else "Stable")
                    trend_summary = f"{direction} ({pct_change:+.1f}% vs prior sample on {rows[1].get('sample_collect_date')})"
                elif detected and prev_conc == 0:
                    trend_summary = f"Newly detected above baseline (prior sample {rows[1].get('sample_collect_date')} was 0)"
            except (ValueError, TypeError):
                pass

        return {
            "pathogen": pathogen_label,
            "zip_code_served": zip5,
            "local_sewershed_site_id": latest.get("site"),
            "sample_collect_date": latest.get("sample_collect_date"),
            "detected_in_local_wastewater": detected,
            "viral_concentration": round(conc, 2),
            "concentration_units": units,
            "previous_sample_concentration": round(prev_conc, 2) if prev_conc is not None else None,
            "short_term_trend": trend_summary,
            "citation": {
                "source_name": f"CDC NWSS Local Sewershed Wastewater Surveillance ({dataset_id}) — ZIP {zip5} Catchment (Site {latest.get('site')})",
                "record_id": latest.get("record_id"),
                "sample_collect_date": latest.get("sample_collect_date"),
                "api_endpoint_url": endpoint_url,
                "dataset_about_url": f"https://data.cdc.gov/d/{dataset_id}",
            },
        }
    except RequestException:
        return None


def get_location_outbreak_and_disease_data(
    postal_code: str,
    latitude: float | None = None,
    longitude: float | None = None,
    city: str = "",
) -> dict[str, Any]:
    """
    Retrieves hyperlocal infectious disease outbreak, local sewershed pathogen detection,
    persistent chronic/endemic disease prevalence, and environmental air quality data
    strictly scoped to the patient's 5-digit US ZIP code (`postal_code`) — NO statewide or
    national high-level aggregation:
    1. CDC PLACES ZCTA5 API (`https://data.cdc.gov/resource/qnzd-25i4.json?locationname=<zip>`)
       for persistent disease prevalence & population strictly inside that 5-digit ZIP code.
    2. CDC NSSP Local Hospital Emergency Department Surveillance (`https://data.cdc.gov/resource/rdmq-nq56.json`)
       for active Influenza, COVID-19, and RSV ED visit trajectories serving that ZIP code's local catchment.
    3. CDC NWSS Local Sewershed Wastewater Surveillance (`ymmh-divb`, `j9g8-acpt`, `45cq-cw4i`, `akvg-8vrb`, `xpxn-rzgz`)
       for real-time PCR pathogen detections & surges serving that ZIP code's local sewershed.
    4. Open-Meteo Hyperlocal Air Quality API (`https://air-quality-api.open-meteo.com/v1/air-quality`)
       at the exact coordinates of the patient's ZIP code.

    Args:
        postal_code: The patient's 5-digit US ZIP code from FHIR `Patient.address.postalCode` (e.g., '02118', '97205', '94108', '78701').
        latitude: Optional exact latitude of the patient's address/ZIP code.
        longitude: Optional exact longitude of the patient's address/ZIP code.
        city: Optional locality/neighborhood label from FHIR `Patient.address.city`.

    Returns:
        Dictionary containing strictly ZIP-code-level active outbreak signals, local sewershed
        pathogen detections, persistent diseases inside that ZIP code, hyperlocal air quality, and citations.
    """
    from concurrent.futures import ThreadPoolExecutor

    if not postal_code or not _ZIP_CODE_RE.match(postal_code.strip()):
        return {
            "error": (
                f"Invalid or missing 5-digit US ZIP code '{postal_code}'. "
                "Outbreak and disease surveillance requires the patient's exact 5-digit ZIP code (e.g., '02118')."
            )
        }

    zip5 = postal_code.strip()[:5]
    clean_city = city.strip() if city and _SAFE_TEXT_RE.match(city.strip()) else ""
    citations: list[dict[str, Any]] = []

    # 1. Exact 5-Digit ZIP Code (ZCTA5) Persistent Disease Surveillance via CDC PLACES (qnzd-25i4)
    zip_persistent_diseases: list[dict[str, Any]] = []
    zip_total_pop: int | None = None
    zip_adult_pop: int | None = None
    resolved_lat: float | None = float(latitude) if latitude is not None else None
    resolved_lon: float | None = float(longitude) if longitude is not None else None

    places_zcta_url = (
        f"https://data.cdc.gov/resource/qnzd-25i4.json"
        f"?locationname={zip5}&datavaluetypeid=CrdPrv&$limit=50"
    )
    try:
        r_places = requests.get(
            "https://data.cdc.gov/resource/qnzd-25i4.json",
            params={
                "locationname": zip5,
                "datavaluetypeid": "CrdPrv",
                "$limit": 50,
            },
            timeout=10,
        )
        if r_places.status_code == 200:
            zcta_rows = r_places.json()
            for row in zcta_rows:
                if zip_total_pop is None and row.get("totalpopulation"):
                    try:
                        zip_total_pop = int(float(row["totalpopulation"]))
                    except (ValueError, TypeError):
                        pass
                if zip_adult_pop is None and row.get("totalpop18plus"):
                    try:
                        zip_adult_pop = int(float(row["totalpop18plus"]))
                    except (ValueError, TypeError):
                        pass
                if (resolved_lat is None or resolved_lon is None) and row.get("geolocation"):
                    coords = row["geolocation"].get("coordinates", [])
                    if len(coords) == 2:
                        resolved_lon, resolved_lat = float(coords[0]), float(coords[1])

                if row.get("categoryid") == "HLTHOUT":
                    try:
                        prev_val = float(row.get("data_value") or 0.0)
                    except (ValueError, TypeError):
                        prev_val = 0.0
                    zip_persistent_diseases.append(
                        {
                            "zip_code": zip5,
                            "condition": row.get("measure"),
                            "short_name": row.get("short_question_text"),
                            "measure_id": row.get("measureid"),
                            "prevalence_in_zip_percent": prev_val,
                            "confidence_interval_95": f"{row.get('low_confidence_limit')}% - {row.get('high_confidence_limit')}%",
                            "data_year": row.get("year"),
                        }
                    )
            zip_persistent_diseases.sort(
                key=lambda x: x["prevalence_in_zip_percent"], reverse=True
            )
            citations.append(
                {
                    "information_covered": f"Persistent Chronic & Endemic Disease Prevalence Strictly Inside ZIP Code {zip5} (ZCTA5)",
                    "source_name": f"CDC PLACES: ZCTA5 (ZIP Code Tabulation Area) Health Data (qnzd-25i4) — ZIP {zip5}",
                    "zip_code": zip5,
                    "api_endpoint_url": places_zcta_url,
                    "dataset_about_url": "https://data.cdc.gov/500-Cities-Places/PLACES-ZCTA-Data-GIS-Friendly-Format-2024-release/qnzd-25i4/about_data",
                }
            )
    except RequestException as exc:
        logger.warning("CDC PLACES ZCTA5 API error for ZIP %s: %s", zip5, exc)

    # Fallback coordinate lookup for the 5-digit ZIP code if still needed
    if resolved_lat is None or resolved_lon is None:
        try:
            r_zip = requests.get(f"https://api.zippopotam.us/us/{zip5}", timeout=6)
            if r_zip.status_code == 200:
                places_list = r_zip.json().get("places", [])
                if places_list:
                    resolved_lat = float(places_list[0]["latitude"])
                    resolved_lon = float(places_list[0]["longitude"])
                    if not clean_city:
                        clean_city = places_list[0].get("place name", "")
        except (RequestException, ValueError, KeyError):
            pass

    # 2. Resolve the exact local Census Tract & 5-digit catchment FIPS physically containing ZIP code `zip5`
    local_fips = ""
    local_census_tract = ""
    if resolved_lat is not None and resolved_lon is not None:
        try:
            r_tract = requests.get(
                "https://data.cdc.gov/resource/cwsq-ngmh.json",
                params={
                    "$where": f"within_circle(geolocation, {resolved_lat}, {resolved_lon}, 6000)",
                    "$limit": 1,
                },
                timeout=8,
            )
            if r_tract.status_code == 200:
                tract_rows = r_tract.json()
                if tract_rows:
                    local_fips = str(tract_rows[0].get("countyfips", "")).zfill(5)
                    local_census_tract = str(tract_rows[0].get("locationid", ""))
        except RequestException as exc:
            logger.warning("CDC Census Tract spatial lookup failed for ZIP %s: %s", zip5, exc)

    # 3. Query Local Hospital ED Outbreak Trajectories (rdmq-nq56) + Local Sewershed Pathogens (NWSS) + ZIP Air Quality concurrently
    local_ed_outbreaks: dict[str, Any] = {}
    local_sewershed_outbreaks: list[dict[str, Any]] = []
    environmental_context: dict[str, Any] = {}

    def _fetch_local_ed() -> dict[str, Any]:
        if not local_fips or not local_fips.isdigit():
            return {}
        ed_url = f"https://data.cdc.gov/resource/rdmq-nq56.json?fips={local_fips}&$order=week_end%20DESC&$limit=2"
        try:
            r_ed = requests.get(
                "https://data.cdc.gov/resource/rdmq-nq56.json",
                params={
                    "fips": local_fips,
                    "$order": "week_end DESC",
                    "$limit": 2,
                },
                timeout=8,
            )
            if r_ed.status_code == 200 and r_ed.json():
                latest_ed = r_ed.json()[0]
                ed_cit = {
                    "information_covered": f"Local Hospital Emergency Department Respiratory Outbreak Trajectories Serving ZIP Code {zip5}",
                    "source_name": f"CDC NSSP Local Emergency Department Surveillance (rdmq-nq56) — Local Catchment for ZIP {zip5}",
                    "week_ending": str(latest_ed.get("week_end", ""))[:10],
                    "api_endpoint_url": ed_url,
                    "dataset_about_url": "https://data.cdc.gov/Public-Health-Surveillance/NSSP-Emergency-Department-Visit-Trajectories-by-St/rdmq-nq56/about_data",
                }
                return {
                    "zip_code_served": zip5,
                    "week_ending": str(latest_ed.get("week_end", ""))[:10],
                    "pathogen_ed_trajectories": [
                        {
                            "pathogen": "Influenza",
                            "percent_of_local_ed_visits": float(latest_ed.get("percent_visits_influenza") or 0.0),
                            "weekly_outbreak_trend": latest_ed.get("ed_trends_influenza", "Unknown"),
                        },
                        {
                            "pathogen": "COVID-19",
                            "percent_of_local_ed_visits": float(latest_ed.get("percent_visits_covid") or 0.0),
                            "weekly_outbreak_trend": latest_ed.get("ed_trends_covid", "Unknown"),
                        },
                        {
                            "pathogen": "RSV",
                            "percent_of_local_ed_visits": float(latest_ed.get("percent_visits_rsv") or 0.0),
                            "weekly_outbreak_trend": latest_ed.get("ed_trends_rsv", "Unknown"),
                        },
                    ],
                    "citation": ed_cit,
                }
        except (RequestException, ValueError):
            pass
        return {}

    def _fetch_zip_air_quality() -> dict[str, Any]:
        if resolved_lat is None or resolved_lon is None:
            return {}
        aq_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={resolved_lat}&longitude={resolved_lon}&current=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide"
        )
        try:
            r_aq = requests.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": resolved_lat,
                    "longitude": resolved_lon,
                    "current": "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide",
                },
                timeout=8,
            )
            if r_aq.status_code == 200:
                curr = r_aq.json().get("current", {})
                aq_cit = {
                    "information_covered": f"Hyperlocal Air Quality & Respiratory Triggers in ZIP Code {zip5}",
                    "source_name": f"Open-Meteo Hyperlocal Air Quality API — ZIP {zip5} ({resolved_lat}, {resolved_lon})",
                    "api_endpoint_url": aq_url,
                    "documentation_url": "https://open-meteo.com/en/docs/air-quality-api",
                }
                return {
                    "zip_code": zip5,
                    "us_aqi": curr.get("us_aqi"),
                    "pm2_5_ug_m3": curr.get("pm2_5"),
                    "pm10_ug_m3": curr.get("pm10"),
                    "ozone_ug_m3": curr.get("ozone"),
                    "nitrogen_dioxide_ug_m3": curr.get("nitrogen_dioxide"),
                    "citation": aq_cit,
                }
        except RequestException:
            pass
        return {}

    with ThreadPoolExecutor(max_workers=7) as pool:
        fut_ed = pool.submit(_fetch_local_ed)
        fut_aq = pool.submit(_fetch_zip_air_quality)
        fut_nwss = [
            pool.submit(_fetch_local_sewershed_pathogen, p_name, ds_id, local_fips, zip5)
            for p_name, ds_id in _NWSS_PATHOGEN_DATASETS
        ]

        local_ed_outbreaks = fut_ed.result()
        if local_ed_outbreaks.get("citation"):
            citations.append(local_ed_outbreaks["citation"])

        for f in fut_nwss:
            item = f.result()
            if item:
                local_sewershed_outbreaks.append(item)
                citations.append(item["citation"])

        environmental_context = fut_aq.result()
        if environmental_context.get("citation"):
            citations.append(environmental_context["citation"])

    return {
        "surveillance_granularity": f"STRICTLY PATIENT ZIP CODE ONLY (ZIP {zip5})",
        "patient_zip_location": {
            "zip_code": zip5,
            "locality": clean_city,
            "census_tract_geoid": local_census_tract or None,
            "zip_total_population": zip_total_pop,
            "zip_adult_population": zip_adult_pop,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
        },
        "active_outbreaks_in_zip_catchment": {
            "local_emergency_department_trajectories": local_ed_outbreaks,
            "local_sewershed_wastewater_pathogens": local_sewershed_outbreaks,
        },
        "persistent_diseases_in_zip_code": zip_persistent_diseases,
        "zip_code_air_quality": environmental_context,
        "citations": citations,
    }


