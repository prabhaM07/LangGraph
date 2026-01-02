from langchain_core.tools import tool
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

@tool
def get_travel_recommendations(pdf_path: str, user_query: str) -> str:
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
        from multi_ai_agent.rag.app import initialize_travel_pipeline
        
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                # Run the async code
                async def _get_recommendations():
                    generator = await initialize_travel_pipeline(pdf_path)
                    response = await generator.generate_response(user_query)
                    return response
                
                result = new_loop.run_until_complete(_get_recommendations())
                return result
            finally:
                new_loop.close()
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            return future.result(timeout=120)  
        
    except FileNotFoundError as e:
        return f"Error: PDF file not found - {str(e)}"
    except TimeoutError:
        return "Error: PDF processing timed out (exceeded 2 minutes)"
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"