import os
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool
def search_travel_destinations(query: str) -> str:
    """Search the web for travel information about destinations, activities, attractions, and tips.
    
    Args:
        query: Search query about travel destinations (e.g., 'best places to visit in Finland', 
               'things to do in Iceland', 'budget hotels in Bangkok')
    
    Returns:
        Web search results with relevant travel information, descriptions, and links
    """
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return "Error: Search service is not configured. Please check API key settings."
        
        search = TavilySearch(max_results=3, api_key=tavily_key)  # Reduced to 3 results
        results = search.invoke(query)
        
        # Handle different result formats
        if not results:
            return f"No results found for '{query}'. Try rephrasing your search or being more specific."
        
        # Simple, clean formatting
        output = f"**Travel Suggestions for '{query}'**\n\n"
        
        # Process results
        if isinstance(results, dict):
            if 'results' in results and isinstance(results['results'], list):
                for i, item in enumerate(results['results'][:3], 1):
                    title = item.get('title', f'Suggestion {i}')
                    content = item.get('content', item.get('snippet', ''))
                    
                    # Keep it concise
                    if len(content) > 200:
                        content = content[:200] + "..."
                    
                    output += f"{i}. **{title}**\n"
                    if content:
                        output += f"   {content}\n\n"
                    else:
                        output += "\n"
                        
        elif isinstance(results, list):
            for i, item in enumerate(results[:3], 1):
                if isinstance(item, dict):
                    title = item.get('title', f'Destination {i}')
                    content = item.get('content', item.get('description', item.get('snippet', '')))
                    
                    if len(content) > 150:
                        content = content[:150] + "..."
                    
                    output += f"{i}. **{title}**\n"
                    if content:
                        output += f"   {content}\n\n"
                    else:
                        output += "\n"
        
        # Add one-line practical tip
        output += "**Tip:** Check visa requirements and weather conditions before planning your trip."
        
        return output
        
    except Exception as e:
        return f"Search error: {str(e)}. Please try again or rephrase your query."