# utils/display.py
def display_results(response):
    """Display the travel agent results in a formatted way"""
    
    print("\n" + "="*80)
    print("TRAVEL PLANNING RESULTS")
    print("="*80)
    
    # Display final result
    final_result = response.get("final_result", "")
    if final_result:
        print(f"\n{final_result}\n")
    else:
        print("\nNo results generated.\n")
    
    # Display agent activity log
    print("-"*80)
    print("AGENT ACTIVITY LOG")
    print("-"*80)
    
    agent_messages = response.get("agent_messages", [])
    if agent_messages:
        for msg in agent_messages:
            print(f"  • {msg}")
    else:
        print("  • No activity logged")
    
    # Debug: Show tool calls if available
    messages = response.get("messages", [])
    tool_calls_found = []
    tool_results_found = []
    
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_found.append(f"{tc['name']}({tc.get('args', {})})")
        if hasattr(msg, "name") and msg.name:  # ToolMessage
            tool_results_found.append(msg.name)
    
    if tool_calls_found:
        print("\n" + "-"*80)
        print("TOOLS CALLED")
        print("-"*80)
        for tc in tool_calls_found:
            print(f"  • {tc}")
    
    if tool_results_found:
        print("\n" + "-"*80)
        print("TOOLS EXECUTED")
        print("-"*80)
        for tr in tool_results_found:
            print(f"  • {tr}")
    
    print("\n" + "="*80 + "\n")