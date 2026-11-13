try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as FastMCP
import logging
from requests.exceptions import HTTPError, RequestException
import uvicorn
import requests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_patient_everything(
    resource_id: str,
) -> dict | None:
    """
    Fetches all resources in a patient's compartment ($everything) from a GCP FHIR store.

    This is a helper function that handles the direct API communication with
    the Google Cloud Healthcare API.

    Args:
        project_id: The Google Cloud project ID.
        location: The dataset's location (e.g., 'asia-east1').
        dataset_id: The parent dataset ID.
        fhir_store_id: The FHIR store ID.
        patient_id: The patient's FHIR resource ID.

    Returns:
        A dictionary (parsed JSON) of the FHIR Bundle if successful,
        otherwise None.
    """
    # Imports Python's built-in "os" module
    import os
    import google
    import json

    # Imports the google.auth.transport.requests transport
    from google.auth.transport import requests

    # Imports a module to allow authentication using a service account
    from google.oauth2 import service_account

    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gsd-argolis-playground")  # replace with your GCP project ID
    location = os.getenv("FHIR_DATASET_LOCATION", "asia-east1")  # replace with the parent dataset's location
    dataset_id = os.getenv("FHIR_DATASET_ID", "test")  # replace with the FHIR store's parent dataset ID
    fhir_store_id = os.getenv("FHIR_STORE_ID", "synthe_data")  # replace with the FHIR store's ID

    try:
        scoped_credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        # Creates a requests Session object with the credentials.
        session = requests.AuthorizedSession(scoped_credentials)

        # URL to the Cloud Healthcare API endpoint and version
        base_url = "https://healthcare.googleapis.com/v1"

        # TODO(developer): Uncomment these lines and replace with your values.
        # project_id = 'my-project'  # replace with your GCP project ID
        # location = 'us-central1'  # replace with the parent dataset's location
        # dataset_id = 'my-dataset'  # replace with the parent dataset's ID
        # fhir_store_id = 'my-fhir-store' # replace with the FHIR store ID
        # resource_id = 'b682d-0e-4843-a4a9-78c9ac64'  # replace with the Patient resource's ID
        url = f"{base_url}/projects/{project_id}/locations/{location}"

        resource_path = "{}/datasets/{}/fhirStores/{}/fhir/{}/{}".format(
            url, dataset_id, fhir_store_id, "Patient", resource_id
        )
        resource_path += "/$everything"

        # Sets required application/fhir+json header on the request
        headers = {"Content-Type": "application/fhir+json;charset=utf-8"}

        response = session.get(resource_path, headers=headers, timeout=10)
        response.raise_for_status()

        resource = response.json()

        #print(json.dumps(resource, indent=2))

        return resource
    
    except (google.auth.exceptions.DefaultCredentialsError, google.auth.exceptions.RefreshError) as auth_err:
        logging.warning(f"GCP ADC reauthentication needed (`gcloud auth application-default login`): {auth_err}")
        return None
    except HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err} - {http_err.response.text}")
        return None
    except RequestException as req_err:
        logging.error(f"A network or request error occurred: {req_err}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred in get_patient_everything: {e}", exc_info=True)
        return None


def list_fhir_patients() -> dict | None:
    """
    Fetches all Patient resources currently registered in the GCP Cloud Healthcare FHIR store.
    """
    import os
    from pathlib import Path
    import google
    from google.auth.transport import requests as grequests
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gsd-argolis-playground")
    location = os.getenv("FHIR_DATASET_LOCATION", "asia-east1")
    dataset_id = os.getenv("FHIR_DATASET_ID", "test")
    fhir_store_id = os.getenv("FHIR_STORE_ID", "synthe_data")

    try:
        scoped_credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = grequests.AuthorizedSession(scoped_credentials)
        base_url = "https://healthcare.googleapis.com/v1"
        resource_path = (
            f"{base_url}/projects/{project_id}/locations/{location}"
            f"/datasets/{dataset_id}/fhirStores/{fhir_store_id}/fhir/Patient"
        )
        headers = {"Accept": "application/fhir+json"}
        response = session.get(resource_path, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error listing FHIR patients: {e}")
        return None


def list_active_triage_encounters() -> dict | None:
    """
    Fetches active (`status=in-progress`) Emergency Ward triage Encounter resources from GCP FHIR store.
    """
    import os
    from pathlib import Path
    import google
    from google.auth.transport import requests as grequests
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gsd-argolis-playground")
    location = os.getenv("FHIR_DATASET_LOCATION", "asia-east1")
    dataset_id = os.getenv("FHIR_DATASET_ID", "test")
    fhir_store_id = os.getenv("FHIR_STORE_ID", "synthe_data")

    try:
        scoped_credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = grequests.AuthorizedSession(scoped_credentials)
        base_url = "https://healthcare.googleapis.com/v1"
        resource_path = (
            f"{base_url}/projects/{project_id}/locations/{location}"
            f"/datasets/{dataset_id}/fhirStores/{fhir_store_id}/fhir/Encounter"
        )
        headers = {"Accept": "application/fhir+json"}
        response = session.get(resource_path, params={"status": "in-progress"}, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error listing FHIR triage encounters: {e}")
        return None


# Create an MCP server
mcp = FastMCP()

@mcp.tool()
def get_medication_details(patient_id: str) -> dict:
    """
    Retrieves the latest 'MedicationRequest' resource for a given patient.

    Args:
        patient_id: The unique FHIR identifier for the patient.

    Returns:
        A dictionary representing the FHIR MedicationRequest resource
        if one is found, otherwise error message.
    """
    patient_details = get_patient_everything(patient_id)
    medication = None
    if patient_details is None:
        return {"error": "Patient details not Found, please check the patient id."}
    medication_list = []
    for i in range(len(patient_details["entry"])):
        if patient_details["entry"][i]["resource"]["resourceType"] == "MedicationRequest":
            medication = patient_details["entry"][i]["resource"]
            medication_list.append(medication)
    
    if medication is not None:
        return {"medication list": medication_list}

    return {"status": "Patient details found, but medication details not found"}

@mcp.tool()

def get_adverse_effects(drug_name):
    """
    Fetches the top 5 reported adverse effects for a given drug from openFDA
    and returns them as a dictionary.

    Args:
        drug_name (str): The name of the drug to search for (e.g., "aspirin").
        
    Returns:
        dict: A dictionary where keys are the adverse effect terms (str)
              and values are the report counts (int).
              In case of an error, returns a dictionary with an 'error' key.
              Returns an empty dictionary if no results are found.
    """
    
    # The API endpoint for drug adverse events
    base_url = "https://api.fda.gov/drug/event.json"
    
    # --- Parameters for the API call ---
    params = {
        # 1. Search for reports where the drug name is listed.
        'search': f'patient.drug.medicinalproduct:"{drug_name.lower()}"',
        
        # 2. Count the unique adverse reaction terms (MedDRA terms)
        'count': 'patient.reaction.reactionmeddrapt.exact',
        
        # 3. Limit the number of results
        'limit': 10
    }

    try:
        # Send the GET request to the openFDA API
        response = requests.get(base_url, params=params)
        
        # Check for a successful response (HTTP 200)
        if response.status_code == 200:
            data = response.json()
            
            # The results are in the 'results' key
            if 'results' in data and data['results']:
                # Use a dictionary comprehension to build the result dictionary
                results_dict = {
                    effect.get('term', 'Unknown Effect'): effect.get('count', 0)
                    for effect in data['results']
                }
                return results_dict
            
            # Handle cases where the drug is found but has no results
            elif 'results' in data and not data['results']:
                return {"error": "Unable to retrieve adverse effects for the drug"}
            
            # Handle API errors (e.g., drug not found, bad query)
            elif 'error' in data:
                return {"error": data['error'].get('message', 'Unknown error')}

        else:
            # Handle non-200 HTTP status codes
            return {
                "error": f"API returned status code {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        # Handle network or connection errors
        return {"error": f"A network error occurred: {e}"}

@mcp.tool()
def list_ward_patients() -> dict:
    """
    Lists all patients currently registered in the Emergency Ward FHIR store.
    """
    try:
        from .clinical_tools import list_emergency_ward_patients
    except ImportError:
        from clinical_tools import list_emergency_ward_patients  # type: ignore
    return list_emergency_ward_patients()


@mcp.tool()
def fetch_patient_clinical_profile(patient_id: str, patient_name: str = "") -> dict:
    """
    Retrieves the complete FHIR ($everything) clinical record for an emergency ward patient,
    including demographics, identity verification against patient_name, residential location
    (city/state/coordinates), current medications, previous medications, active conditions,
    previous conditions, and allergies.
    """
    try:
        from .clinical_tools import get_patient_clinical_profile
    except ImportError:
        from clinical_tools import get_patient_clinical_profile  # type: ignore
    return get_patient_clinical_profile(patient_id=patient_id, patient_name=patient_name)


@mcp.tool()
def verify_drug_brand_or_generic(drug_name: str, rxcui_code: str = "") -> dict:
    """
    Checks whether a prescribed drug in FHIR is an Original (Generic / Active Ingredient) drug name
    or a Brand (Trade) name using the NIH NLM RxNorm REST API and OpenFDA Drug Label/Event APIs.
    """
    try:
        from .clinical_tools import check_drug_brand_or_generic
    except ImportError:
        from clinical_tools import check_drug_brand_or_generic  # type: ignore
    return check_drug_brand_or_generic(drug_name=drug_name, rxcui_code=rxcui_code)


@mcp.tool()
def fetch_location_outbreak_and_disease_data(
    postal_code: str,
    latitude: float | None = None,
    longitude: float | None = None,
    city: str = "",
) -> dict:
    """
    Queries CDC PLACES ZCTA5 (qnzd-25i4), CDC NSSP Local Hospital ED Surveillance (rdmq-nq56),
    CDC NWSS Local Sewershed Wastewater Surveillance, and Open-Meteo Hyperlocal Air Quality
    strictly for the patient's 5-digit ZIP code (`postal_code`).
    """
    try:
        from .clinical_tools import get_location_outbreak_and_disease_data
    except ImportError:
        from clinical_tools import get_location_outbreak_and_disease_data  # type: ignore
    return get_location_outbreak_and_disease_data(
        postal_code=postal_code, latitude=latitude, longitude=longitude, city=city
    )


@mcp.tool()
def fetch_hospitalizations_and_notes(patient_id: str) -> dict:
    """Retrieves longitudinal hospitalizations, ED visits, and specialist consult notes from FHIR."""
    try:
        from .ehr_chart_tools import get_hospitalizations_and_clinical_notes
    except ImportError:
        from ehr_chart_tools import get_hospitalizations_and_clinical_notes  # type: ignore
    return get_hospitalizations_and_clinical_notes(patient_id=patient_id)


@mcp.tool()
def fetch_medication_reconciliation(patient_id: str) -> dict:
    """Retrieves active prescriptions, dose changes, held drugs, and pharmacy adherence barriers from FHIR."""
    try:
        from .ehr_chart_tools import get_medication_reconciliation_history
    except ImportError:
        from ehr_chart_tools import get_medication_reconciliation_history  # type: ignore
    return get_medication_reconciliation_history(patient_id=patient_id)


@mcp.tool()
def fetch_longitudinal_labs_and_imaging(patient_id: str) -> dict:
    """Retrieves multi-date lab trajectories and diagnostic imaging reports (CT, TTE, CXR) from FHIR."""
    try:
        from .ehr_chart_tools import get_longitudinal_labs_and_imaging
    except ImportError:
        from ehr_chart_tools import get_longitudinal_labs_and_imaging  # type: ignore
    return get_longitudinal_labs_and_imaging(patient_id=patient_id)


@mcp.tool()
def fetch_open_loops_and_care_gaps(patient_id: str) -> dict:
    """Retrieves unresolved clinical safety alerts, unreviewed labs, and care gaps from FHIR Flag resources."""
    try:
        from .ehr_chart_tools import get_open_loops_and_care_gaps
    except ImportError:
        from ehr_chart_tools import get_open_loops_and_care_gaps  # type: ignore
    return get_open_loops_and_care_gaps(patient_id=patient_id)


@mcp.tool()
def build_clinical_swimlane_graph(patient_id: str) -> dict:
    """Generates the 4-Track Interactive Clinical Swimlane Graph (Mermaid, Markdown matrix, HTML/SVG) from FHIR."""
    try:
        from .ehr_chart_tools import generate_clinical_swimlane_graph
    except ImportError:
        from ehr_chart_tools import generate_clinical_swimlane_graph  # type: ignore
    return generate_clinical_swimlane_graph(patient_id=patient_id)


if __name__ == "__main__":
    uvicorn.run(mcp.streamable_http_app, host="localhost", port=8080)