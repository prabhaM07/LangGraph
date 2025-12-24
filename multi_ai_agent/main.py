from typing import Optional
from utils import display_results
from workflow import create_travel_workflow
from langchain_core.messages import HumanMessage

def run_travel_agent(user_query: str, pdf_path: Optional[str] = None):
    graph = create_travel_workflow()
    
    mermaid_code = graph.get_graph().draw_mermaid()
    print(mermaid_code)
    print("\n Copy the code above and paste it into: https://mermaid.live/")
    
    initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "user_query": user_query,
            "agent_messages": []
        }
    
    if pdf_path:
            initial_state["pdf_path"] = pdf_path
            
    try:
        response = graph.invoke(initial_state)
        
        display_results(response)
        
        return response
        
    except Exception as e:
        return None
    

if __name__ == "__main__":

    user_query = input(" Enter your travel query: ").strip()
    
    if not user_query:
        print("Query cannot be empty!")
        exit(1)
    
    pdf_path = input(" PDF path (press Enter to skip): ").strip()
    pdf_path = pdf_path if pdf_path else None
    
    print("\n Processing your request...\n")
    
    # Run agent
    run_travel_agent(user_query, pdf_path)