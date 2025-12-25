
from langchain_core.tools import tool

from tools.rag.app import initialize_travel_pipeline



@tool
async def get_travel_recommendations(pdf_path: str, user_query: str) -> str:
    """
    Get personalized travel destination recommendations from a travel agency brochure.
    
    This tool analyzes a travel catalog PDF and provides destination suggestions based on
    user preferences for activities, locations, budget, or travel style.
    
    Args:
        pdf_path: Path to the travel agency brochure/catalog PDF file
        user_query: User's travel preferences or questions (e.g., "I want beach destinations 
                   with water sports", "Suggest romantic honeymoon destinations", 
                   "What mountain adventure packages are available?")
    
    Returns:
        Personalized travel recommendations with destinations, activities, and package details
    """
    try:
        
        # Initialize pipeline
        generator = await initialize_travel_pipeline(pdf_path)
        
        # Generate recommendations
        response = await generator.generate_response(user_query)
        
        return response
        
    except FileNotFoundError as e:
        return f"Error: PDF file not found - {str(e)}"
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"