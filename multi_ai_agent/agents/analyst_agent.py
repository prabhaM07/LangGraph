from typing import Dict
from langchain_core.messages import AIMessage
from dotenv import load_dotenv

from tools.SQL_query import query_sql_database
from travelState import TravelState

load_dotenv()


def analyst_agent(state: TravelState) -> Dict:
    """Query database for travel destinations"""
    
    user_preferences = state.get("user_preferences")
    
    print("\nANALYST: Querying database...")
    
    # Query database
    result = query_sql_database.invoke({"user_preferences": user_preferences})
    
    # Generate message based on results
    if result.get("count", 0) > 0:
        msg = f"Analyst: Found {result["count"]} destinations in database"
        print(f" {msg}")
    else:
        msg = "Analyst: No database results found"
        print(f"{msg}")
    
    return {
        "messages": [AIMessage(content=msg)],
        "db_results": result,
        "next_agent": "supervisor",
        "agent_messages": state.get("agent_messages", []) + [msg]
    }
    