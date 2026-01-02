# utils/user_query.py
from travelState import TravelState

def get_user_query(state: TravelState) -> str:
    """Extract user query from state"""
    return state.get("user_query", "")

# utils/display.py
def display_results(state):
    """Display formatted results"""
    print("\n" + "="*80)
    print("🎉 FINAL TRAVEL PLAN")
    print("="*80 + "\n")
    
    final = state.get("final_result", "No results available")
    print(final)
    
    print("\n" + "="*80)
    print("📊 Execution Summary:")
    print("="*80)
    
    agent_msgs = state.get("agent_messages", [])
    if agent_msgs:
        print("\n🔄 Workflow Steps:")
        for msg in agent_msgs:
            print(f"  {msg}")
    
    print("\n" + "="*80)