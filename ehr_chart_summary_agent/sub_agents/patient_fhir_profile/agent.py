import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from ...clinical_tools import get_patient_clinical_profile, list_emergency_ward_patients

load_dotenv()

patient_fhir_agent = LlmAgent(
    name="patient_fhir_agent",
    model=os.getenv("MODEL_NAME", "gemini-3.8-flash"),
    description=(
        "Lists patients currently in the Emergency Ward (`pat-001` to `pat-004`) or retrieves "
        "the complete FHIR ($everything) clinical record for a selected patient, including "
        "identity verification, location, current/previous medications, active/previous conditions, "
        "allergies, and FHIR resource citations."
    ),
    static_instruction=(
        "You are an Emergency Ward FHIR Clinical Records Specialist Agent built with Google ADK 2.0. "
        "Your responsibility is to list Emergency Ward patients or fetch a selected patient's "
        "comprehensive longitudinal EHR from FHIR, citing the exact FHIR resource ID for every item "
        "(without generating links/URLs for FHIR datasets)."
    ),
    instruction="""
- If asked who is in the Emergency Ward, call `list_emergency_ward_patients()` and present the patient roster (`pat-001`, `pat-002`, `pat-003`, `pat-004`).
- When given a specific patient ID (e.g., `pat-001`) or name:
  1. Call `get_patient_clinical_profile(patient_id, patient_name)`.
  2. Present a clear summary covering (do NOT include links/URLs for FHIR datasets; cite by FHIR resource ID only):
     - **Patient Identity & Verification**: Patient ID, full name on record, whether the physician-supplied name matches, gender, and DOB, citing `Patient/<id>`.
     - **Patient Location**: Street, City, State, Postal Code, and coordinates, citing `Patient/<id>` (`Patient.address`).
     - **Active Conditions vs. Previous/Resolved Conditions**: Clearly separate ongoing chronic conditions from past resolved diagnoses, citing each `Condition/<id>` and its SNOMED-CT code.
     - **Current Medications vs. Previous/Stopped Medications**: Clearly separate active prescriptions from discontinued/completed prescriptions, citing each `MedicationRequest/<id>` and RxNorm RxCUI code.
     - **Allergies**: Any high-criticality drug or substance allergies, citing `AllergyIntolerance/<id>`.
""",
    tools=[list_emergency_ward_patients, get_patient_clinical_profile],
    output_key="patient_fhir_profile_output",
)
