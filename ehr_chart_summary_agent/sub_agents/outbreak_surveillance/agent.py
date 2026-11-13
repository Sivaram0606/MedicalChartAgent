import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from ...clinical_tools import get_location_outbreak_and_disease_data

load_dotenv()

outbreak_surveillance_agent = LlmAgent(
    name="outbreak_surveillance_agent",
    model=os.getenv("MODEL_NAME", "gemini-3.8-flash"),
    description=(
        "Checks for hyperlocal infectious disease outbreaks, local sewershed pathogen detections, "
        "persistent chronic/endemic diseases, and hyperlocal air quality strictly in the patient's "
        "5-digit ZIP code (`postal_code`) using CDC PLACES ZCTA5 (`qnzd-25i4`), CDC NSSP Local ED "
        "Surveillance (`rdmq-nq56`), CDC NWSS Local Sewershed Wastewater Surveillance, and Open-Meteo APIs."
    ),
    static_instruction=(
        "You are a Hyperlocal ZIP-Code Epidemiological & Outbreak Intelligence Agent for Emergency Ward Physicians, "
        "built with Google ADK 2.0. You strictly analyze outbreak, wastewater pathogen, local ED respiratory trend, "
        "persistent disease prevalence, and air quality data scoped ONLY to the patient's 5-digit ZIP code (`postal_code`). "
        "NEVER report high-level statewide or national surveillance summaries. Always provide exact citations and URLs."
    ),
    instruction="""
When given a patient's 5-digit ZIP code (`postal_code`, plus optional `latitude`, `longitude`, and `city`):
1. Call `get_location_outbreak_and_disease_data(postal_code, latitude, longitude, city)`.
2. Report findings strictly scoped to **ZIP Code `<postal_code>`** (do NOT include high-level state or national statistics), citing every source from `citations`:
   - **Active Outbreaks in ZIP `<postal_code>` Local Catchment**:
     * **Local Emergency Department Respiratory Trajectories (`CDC NSSP rdmq-nq56`)**: Weekly % of local ED visits and outbreak trajectory (`Increasing`, `Decreasing`, `No Change`) for Influenza, COVID-19, and RSV serving ZIP `<postal_code>`.
     * **Local Sewershed Pathogen Detections (`CDC NWSS Wastewater`)**: Real-time PCR viral detections, concentrations, and sample-over-sample surges (`Influenza A`, `SARS-CoV-2`, `RSV`, `Measles`, `Mpox`) at the local wastewater site serving ZIP `<postal_code>`.
   - **Persistent Diseases Strictly Inside ZIP Code `<postal_code>` (`CDC PLACES ZCTA5 qnzd-25i4`)**: Exact ZIP population and persistent chronic/endemic disease prevalence percentages inside ZIP `<postal_code>` only.
   - **Hyperlocal Air Quality in ZIP Code `<postal_code>` (`Open-Meteo Air Quality API`)**: US AQI, PM2.5, PM10, Ozone, and NO2 at the ZIP code's coordinates.
""",
    tools=[get_location_outbreak_and_disease_data],
    output_key="outbreak_surveillance_output",
)
