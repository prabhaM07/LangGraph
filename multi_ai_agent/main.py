from utils.display import display_results
from workflow import create_travel_workflow
import asyncio

def run_travel_agent(user_query: str, pdf_path: str = None):
    """Run the travel agent with a user query"""
    
    print("\n🌍 Initializing Travel Planning Agent...\n")
    
    # Create workflow
    graph = create_travel_workflow()
    
    # Optional: Display graph structure
    try:
        mermaid_code = graph.get_graph().draw_mermaid()
        print("Graph Structure (paste into https://mermaid.live/):")
        print(mermaid_code)
        print("\n" + "-"*80 + "\n")
    except:
        pass
    
    # Initial state
    initial_state = {
        "messages": [],
        "user_query": user_query,
        "agent_messages": [],
        "task_complete": False,
        "pdf_path": pdf_path,
        "extracted_data": None,
        "web_results": None,
        "weather_results": None,
        "news_results": None,
        "final_result": None,
        "next_agent": None
    }
    
    try:
        print("🔄 Processing your travel request...\n")
        
        # Run workflow
        config = {"configurable": {"thread_id": "travel_session_001"}}
        response = asyncio.run(
            graph.ainvoke(initial_state, config)
        )        
        # Display results
        display_results(response)
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_interactive():
    """Run in interactive mode"""
    
    print("\n" + "="*80)
    print("🌍 TRAVEL PLANNING ASSISTANT")
    print("="*80)
    print("\nWelcome! I can help you plan your travel with:")
    print("  • Real-time weather information")
    print("  • Latest travel news and updates")
    print("  • Web search for destinations and activities")
    print("  • PDF brochure analysis for package recommendations")
    print("\nType 'quit' or 'exit' to end the session.\n")
    print("="*80 + "\n")
    
    while True:
        user_query = input("You: ").strip()
        
        if user_query.lower() in ['quit', 'exit']:
            print("\n✈️  Happy travels! Goodbye!\n")
            break
        
        if not user_query:
            continue
        
        pdf_path = input("PDF path (press Enter to skip): ").strip()
        pdf_path = pdf_path if pdf_path else None
        
        run_travel_agent(user_query, pdf_path)
        print("\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Command line mode
        query = sys.argv[1]
        pdf = sys.argv[2] if len(sys.argv) > 2 else None
        run_travel_agent(query, pdf)
    else:
        # Interactive mode
        run_interactive()