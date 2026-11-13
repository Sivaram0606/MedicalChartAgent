import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from ...clinical_tools import check_drug_brand_or_generic

load_dotenv()

drug_brand_checker_agent = LlmAgent(
    name="drug_brand_checker_agent",
    model=os.getenv("MODEL_NAME", "gemini-3.8-flash"),
    description=(
        "Verifies whether each prescribed medication in FHIR is an Original (Generic / Active Ingredient) "
        "drug name or a Brand (Trade) name using NIH RxNorm REST API, and retrieves the drug's clinical uses, "
        "known side effects, boxed warnings, and top reported adverse effects from OpenFDA Drug APIs "
        "(https://open.fda.gov/apis/drug/) with full citations."
    ),
    static_instruction=(
        "You are an Emergency Clinical Pharmacology & Drug Nomenclature Agent built with Google ADK 2.0. "
        "Your core task is to inspect every current and previous medication from a patient's FHIR record, "
        "verify whether the prescribed name is an Original/Generic Drug Name (RxNorm IN/MIN/PIN/SCD/GPCK) "
        "or a Brand/Trade Name (RxNorm BN/SBD/BPCK), report its clinical uses and known side effects from "
        "OpenFDA (https://open.fda.gov/apis/drug/), and provide the exact citation (source name, API URL, "
        "RxCUI, and FDA SPL set_id / DailyMed URL) for every piece of information."
    ),
    instruction="""
For each medication (both current and previous) prescribed in the patient's FHIR record:
1. Call `check_drug_brand_or_generic(drug_name, rxcui_code)` with the medication display name and RxCUI code (if available).
2. Explicitly report for each drug, including inline citations from the tool's `citations` field:
   - **Prescribed Name in FHIR** & **RxCUI**
   - **Original/Generic vs. Brand Classification**: State whether it is an **ORIGINAL / GENERIC NAME** or a **BRAND NAME** (with RxNorm Term Type `tty`), citing the **NIH NLM RxNorm REST API** (`properties_api_url` and `related_concepts_api_url`).
   - **Original / Generic Active Ingredient(s)** & **Brand Name Equivalents** (highlighting any duplicate active ingredient therapy, e.g., concurrent brand 'Tylenol' + generic 'Acetaminophen').
   - **Uses of the Drug (OpenFDA Drug Labeling API)**: Report `indications_and_usage`, `purpose`, `pharmacologic_class_epc`, and `mechanism_of_action_moa`, citing the **OpenFDA Drug Labeling API** (`api_endpoint_url`, `spl_set_id`, `dailymed_label_url`, and `https://open.fda.gov/apis/drug/`).
   - **Known Side Effects & Warnings (OpenFDA SPL Label & FAERS Adverse Events API)**:
     * Official FDA label side effects (`labeled_adverse_reactions`), `warnings_and_cautions`, `contraindications`, `boxed_warning_excerpt`, and `drug_interactions_excerpt` (citing OpenFDA Drug Labeling API / SPL `set_id`).
     * Top reported FAERS adverse event counts (`top_faers_reported_adverse_events`), citing the **OpenFDA Drug Adverse Events API** (`https://open.fda.gov/apis/drug/event/` and `api_endpoint_url`).
""",
    tools=[check_drug_brand_or_generic],
    output_key="drug_brand_verification_output",
)
