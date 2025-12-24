from typing import Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from dotenv import load_dotenv
from tools.pdf_extractor import extract_travel_pdf
from travelState import TravelState

load_dotenv()

def extractor_agent(state: TravelState) -> Dict:
    """Extract packages from PDF"""
    pdf_path = state.get("pdf_path")
    
    if not pdf_path:
        return {
            "extracted_data": {"error": "No PDF provided", "packages": []},
            "next_agent": "supervisor"
        }
    user_preferences = state.get("user_preferences")
    
    result = extract_travel_pdf.invoke({"pdf_path": pdf_path,"user_preferences" : user_preferences})
    
    packages_count = result.get("total_packages", 0)
    
    success = packages_count > 0
    
    if success:
        msg = f"Extractor: Found {packages_count} packages in PDF"
        print(f"{msg}")
    else:
        error_msg = result.get("error", "Unknown error")
        msg = f"Extractor: PDF extraction failed - {error_msg}"
    
    return {
        "messages": [AIMessage(content=f"{msg}")],
        "extracted_data": result,
        "next_agent": "supervisor",
        "agent_messages": state.get("agent_messages", []) + [msg]
    }
