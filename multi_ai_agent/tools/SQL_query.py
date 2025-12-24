import ast
import os
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from travel_preference import TravelPreference


@tool
def query_sql_database(user_preferences : TravelPreference):
    """Query travel database for matching destinations"""
    
    try :
        db_url = os.getenv("DATABASE_URL")
        if not db_url: 
            return {"error": "DATABASE_URL not configured", "success": False}

        db  = SQLDatabase.from_uri(db_url)
        
        conditions = []
        
        budget = user_preferences.budget_max
        activities = user_preferences.activities
        states = user_preferences.destination_state
        countries = user_preferences.destination_country
        travel_month = user_preferences.travel_month
        
        if budget is not None:
                conditions.append(f"budget_max <= {int(budget)}")
                
        if activities:
                activities_array = "ARRAY[" + ",".join(f"'{a}'" for a in activities) + "]::TEXT[]"
                conditions.append(f"activities && {activities_array}")
                
        if travel_month:
                conditions.append(f"LOWER(travel_month) = LOWER('{travel_month}')")
                
        if states:
                states_array = "ARRAY[" + ",".join(f"'{s}'" for s in states) + "]::TEXT[]"
                conditions.append(f"destination_state && {states_array}")
                
        if countries:
                countries_array = "ARRAY[" + ",".join(f"'{c}'" for c in countries) + "]::TEXT[]"
                conditions.append(f"destination_country && {countries_array}")
                
                
        # Base query
        base_query = """
        SELECT budget_max, activities, travel_month, destination_state, destination_country
        FROM travel_preferences
        """
        
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
        else:
            where_clause = ""
            
        final_query = f"{base_query}{where_clause} LIMIT 10;"
        
        results = db.run(final_query)
        
        if not results or results.strip() == "[]" or results.strip() == "":
            print("No matching results found")
            return {
                "destinations": [],
                "sql_executed": final_query,
                "success": False,
                "source": "database",
                "count": 0
            }
        
        rows = ast.literal_eval(results) if results.strip() else []
        result_count = len(rows)
        
        return {
                "destinations": results,
                "sql_executed": final_query,
                "success": True if result_count > 0 else False,  
                "source": "database",
                "count": result_count
        }
        
    except Exception as e:
        print(f"Database error: {str(e)}")
        return {
            "error": str(e),
            "success": False,
            "source": "database",
            "count": 0
        }
        
        
        