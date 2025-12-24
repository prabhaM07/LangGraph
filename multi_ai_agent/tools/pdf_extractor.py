import json
import os
from langchain_core.tools import tool
from llm import get_llm
from utils import content_correction
from travel_preference import TravelPreference
import pdfplumber


@tool
def extract_travel_pdf(pdf_path: str, user_preferences: TravelPreference):
    """Extract travel packages from PDF catalog"""
    try :
        
        if not os.path.exists(pdf_path):
            return {"error": f"PDF not found: {pdf_path}","packages": [], "total_packages": 0}
        
        full_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            if full_text == "":
                return {"error": "Empty PDF", "packages": [], "total_packages": 0}
        

        llm = get_llm()
        
        pdf_extractor_prompt = f"""Extract travel packages from this PDF text.

        User is looking for:
        - Budget: {user_preferences.budget_max or "Any"} rupees
        - Activities: {user_preferences.activities}
        - States: {user_preferences.destination_state}
        - Countries: {user_preferences.destination_country}
        - Month: {user_preferences.travel_month or "Any"}

        Return ONLY valid JSON following this structure:
        {{
            "packages": [
                {{
                    "destination": "place name",
                    "country": "country name",
                    "price": 25000,
                    "duration_days": 5,
                    "description": "brief description",
                    "activities": ["activity1", "activity2"],
                    "best_season": "season/month"
                }}
            ]
        }}

        Rules:
        - Extract packages that match user preferences
        - Use null for missing fields
        - Use [] for empty lists
        - Return ONLY JSON, no explanation

        PDF Text:
        {full_text[:6000]}

        JSON:"""

        response = llm.invoke(pdf_extractor_prompt)
        
        content = response.content.strip()
        
        content = content_correction(content)
        
        result = json.loads(content.strip())
        
        if "packages" not in result:
                result["packages"] = []
            
        result["total_packages"] = len(result["packages"])
        
        return result
    
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return {"error": str(e), "packages": [], "total_packages": 0}
    
    