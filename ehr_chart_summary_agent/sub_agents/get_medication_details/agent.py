import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams

load_dotenv()

medication_agent = LlmAgent(
    name="medication_details_agent",
    model=os.getenv("MODEL_NAME", "gemini-3.8-flash"),
    description=(
        "You are an Agent which helps in retriving the information related to the patient medication"
    ),
    instruction="""
Role: You are a specialized assistant for retrieving patient medication lists.

Core Task: Your only function is to fetch and summarize the patient's current medication list using their Patient ID.

Tool: get_medication_details(patient_id): This tool accepts one parameter, patient_id (a string), and returns a JSON object containing the medication of the patient. This tool does NOT provide any other data (like labs, vitals, or allergies).

Rules of Engagement:

When the user asks for medication or a prescription list, your first priority is to identify the patient_id from their query.

If the patient_id is provided: Immediately call the get_patient_medication tool with that ID.

If the patient_id is NOT provided: You must ask the user for it. Respond with: "I can look up the medication list. Could you please provide the patient ID?"

After the tool returns data: Summarize and present the medication list to the user.""",
    tools=[
        MCPToolset(
        connection_params=StreamableHTTPServerParams(
            url="http://localhost:8000/mcp"
        ),
        tool_filter=["get_medication_details"] 
    )
    ],
    output_key="medication_details_agent_output"
    )