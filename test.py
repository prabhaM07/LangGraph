import os
from dotenv import load_dotenv
from workflow import create_travel_workflow
from langchain_core.messages import ToolMessage, AIMessage
from langfuse_integration import TravelPlannerObserver

load_dotenv()

def display_results(state):
    """Display final results"""
    final = state.get("final_result", "No result generated")
    print(final)

def run_travel_planner(user_query: str, pdf_path: str = None):
    """Main execution function with Langfuse observability"""
    
    print("\n" + "="*80)
    print("🌍 COMPREHENSIVE TRAVEL PLANNING SYSTEM")
    print("="*80)
    print("\n✨ Features:")
    print("  📅 Day-wise itinerary planning")
    print("  🌤️  Weather-based recommendations")
    print("  🏨 Accommodation suggestions")
    print("  🍽️  Restaurant recommendations")
    print("  🗺️  Route planning (all modes)")
    print("  💰 Budget estimation")
    print("  📄 PDF brochure analysis")
    print("  📊 Langfuse Observability ENABLED")
    print("="*80 + "\n")
    
    # Initialize Langfuse observer
    observer = TravelPlannerObserver()
    trace = observer.start_trace(user_query, pdf_path)
    
    # Create workflow
    graph = create_travel_workflow()
    
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
        "restaurant_results": None,
        "attraction_results": None,
        "route_results": None,
        "final_result": None,
        "next_agent": None,
        "human_feedback": None,
        "human_review_summary": None,
        "awaiting_human_input": False,
        "travel_location": None,
        "travel_dates": None
    }
    
    try:
        print(f"🔄 Processing: '{user_query}'\n")
        print(f"📊 Langfuse Trace ID: {observer.trace_id}\n")
        
        config = {"configurable": {"thread_id": "travel_001"}}
        
        max_iterations = 10
        iteration = 0
        current_node = "START"
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}")
            
            # Execute workflow
            result = None
            for event in graph.stream(initial_state, config, stream_mode="values"):
                result = event
                
                # Log agent execution
                if "agent_messages" in event and event["agent_messages"]:
                    last_msg = event["agent_messages"][-1]
                    print(f"  {last_msg}")
                    
                    # Detect and log which agent executed
                    agent_detected = None
                    msg_lower = last_msg.lower()
                    
                    if "coordinator" in msg_lower:
                        agent_detected = "coordinator"
                    elif "trip_planner" in msg_lower or "trip planner" in msg_lower:
                        agent_detected = "trip_planner"
                    elif "research" in msg_lower:
                        agent_detected = "research_agent"
                    elif "weather" in msg_lower:
                        agent_detected = "weather_analyst"
                    elif "budget" in msg_lower:
                        agent_detected = "budget_analyst"
                    elif "accommodation" in msg_lower or "hotel" in msg_lower:
                        agent_detected = "accommodation_specialist"
                    elif "route" in msg_lower or "direction" in msg_lower:
                        agent_detected = "route_planner"
                    elif "restaurant" in msg_lower or "dining" in msg_lower:
                        agent_detected = "restaurant_suggester"
                    elif "synthesizer" in msg_lower or "final" in msg_lower:
                        agent_detected = "synthesizer"
                    
                    if agent_detected:
                        observer.log_agent_execution(agent_detected, event, last_msg)
                        current_node = agent_detected
                
                # Log tool calls
                if "messages" in event:
                    for msg in event["messages"]:
                        if isinstance(msg, ToolMessage):
                            observer.log_tool_call(
                                tool_name=msg.name,
                                tool_input={"message": "Tool execution"},
                                tool_output=msg.content[:500]
                            )
                        elif isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                            # Log LLM call for tool invocation
                            for tool_call in msg.tool_calls:
                                observer.log_llm_call(
                                    agent_name=current_node,
                                    prompt=str(tool_call.get('args', {})),
                                    response=msg.content if msg.content else "Tool call initiated",
                                    model="llama-3.1-8b-instant"
                                )
            
            # Check completion
            if result and result.get("task_complete"):
                print("\n✅ Planning complete!\n")
                display_results(result)
                
                # Score the final result
                observer.score_final_result(
                    score_name="completeness",
                    value=1.0,
                    comment="Travel plan successfully generated"
                )
                
                # End trace with success
                observer.end_trace(
                    final_result=result.get("final_result", ""),
                    success=True
                )
                
                return result
            
            # Check for human review checkpoint
            snapshot = graph.get_state(config)
            next_node = snapshot.next if hasattr(snapshot, 'next') else None
            
            if next_node and 'human_review' in str(next_node):
                print("\n" + "="*80)
                print("⏸️  HUMAN REVIEW CHECKPOINT")
                print("="*80)
                
                current_state = snapshot.values
                summary = current_state.get("human_review_summary", "")
                
                if not summary:
                    # Generate from messages
                    tool_results = []
                    for msg in current_state.get("messages", []):
                        if isinstance(msg, ToolMessage):
                            content = msg.content[:400] + "..." if len(msg.content) > 400 else msg.content
                            tool_results.append(f"\n🔧 {msg.name}:\n{content}")
                        elif isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
                            content = msg.content[:400] + "..." if len(msg.content) > 400 else msg.content
                            tool_results.append(f"\n🤖 Response:\n{content}")
                    summary = "\n".join(tool_results) if tool_results else "Processing..."
                
                print("\n📋 Current Findings:")
                print("-" * 80)
                print(summary)
                print("-" * 80)
                
                print("\n🤔 Review Options:")
                print("  ✅ 'proceed' or 'approve' - Continue with plan")
                print("  ✏️  'change [detail]' - Modify specific aspect")
                print()
                
                human_input = input("👤 Your response: ").strip().lower()
                
                if not human_input:
                    human_input = "proceed"
                
                print(f"\n✅ Feedback: '{human_input}'")
                print("\n🔄 Continuing to final synthesis...\n")
                
                # Log human review
                observer.log_human_review(summary=summary[:500], feedback=human_input)
                
                # Score based on human feedback
                if "proceed" in human_input or "approve" in human_input:
                    observer.score_final_result(
                        score_name="human_approval",
                        value=1.0,
                        comment="User approved the plan"
                    )
                else:
                    observer.score_final_result(
                        score_name="human_approval",
                        value=0.5,
                        comment=f"User requested changes: {human_input}"
                    )
                
                # Update state
                graph.update_state(
                    config,
                    {
                        "human_feedback": human_input,
                        "awaiting_human_input": False
                    }
                )
                
                initial_state = None
            else:
                break
        
        if result:
            display_results(result)
            observer.end_trace(
                final_result=result.get("final_result", ""),
                success=True
            )
            return result
        else:
            print("⚠️  Workflow incomplete")
            observer.end_trace(
                final_result="Workflow incomplete",
                success=False
            )
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Log error in Langfuse
        observer.end_trace(
            final_result=f"Error: {str(e)}",
            success=False
        )
        
        return None

def interactive_mode():
    """Interactive CLI mode with Langfuse tracking"""
    
    print("\n" + "="*80)
    print("🌍 INTERACTIVE TRAVEL PLANNING ASSISTANT")
    print("="*80)
    print("\n✨ What I can help with:")
    print("  • 'Plan 5 day trip to Japan' - Complete itinerary")
    print("  • 'Weather in Iceland' - Climate info")
    print("  • 'Best places in Kerala' - Destination research")
    print("  • 'Budget for Europe 2 weeks' - Cost estimation")
    print("  • 'Hotels in Dubai' - Accommodation")
    print("\n💡 Features:")
    print("  → PDF brochure analysis")
    print("  → Weather-based planning")
    print("  → Route planning (automatic)")
    print("  → Restaurant suggestions (automatic)")
    print("  → Langfuse observability tracking")
    print("  → Powered by Groq Llama 3.1")
    print("\nType 'quit' or 'exit' to stop.\n")
    print("="*80 + "\n")
    
    while True:
        user_query = input("\n💬 Your travel query: ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'bye']:
            print("\n✈️  Happy travels! Goodbye!\n")
            break
        
        if not user_query:
            continue
        
        pdf_path = input("📄 PDF brochure path (press Enter to skip): ").strip()
        pdf_path = pdf_path if pdf_path else None
        
        if pdf_path and not os.path.exists(pdf_path):
            print(f"⚠️  PDF not found: {pdf_path}")
            pdf_path = None
        
        run_travel_planner(user_query, pdf_path)
        print("\n" + "-"*80)

if __name__ == "__main__":
    import sys
    
    # Display graph structure
    try:
        graph = create_travel_workflow()
        print("\n📊 Workflow Structure:")
        print("START → Coordinator → [Specialist Agent] → Tools → Human Review → Synthesizer → END")
        print("\n📊 Observability: Langfuse tracking enabled")
        print("🤖 LLM Model: Groq Llama 3.1 8B Instant")
        print("   View traces at: https://cloud.langfuse.com")
        print("\n" + "-"*80)
    except Exception as e:
        print(f"Warning: Could not display workflow structure: {e}")
    
    # Check arguments
    if len(sys.argv) > 1:
        query = sys.argv[1]
        pdf = sys.argv[2] if len(sys.argv) > 2 else None
        run_travel_planner(query, pdf)
    else:
        interactive_mode()