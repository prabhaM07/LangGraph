import os
from dotenv import load_dotenv
from workflow import create_travel_workflow
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command

load_dotenv()


def display_results(state):
    print(state.get("final_result", "No result generated"))


def run_travel_planner(user_query: str, pdf_path: str = None):
    graph = create_travel_workflow()

    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "user_query": user_query,
        "agent_messages": [],
        "task_complete": False,
        "pdf_path": pdf_path or "",
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
        "travel_dates": None,
    }

    try:
        config = {"configurable": {"thread_id": "travel_session_001"}}

        result = None
        for event in graph.stream(initial_state, config, stream_mode="values"):
            result = event

        if result and result.get("final_result"):
            print(result["final_result"])

        snapshot = graph.get_state(config)

        query_lower = user_query.lower()
        is_route_only = any(
            kw in query_lower
            for kw in ["route", "direction", "how to get", "travel from"]
        )

        if is_route_only and not (snapshot.next and "ask_for_images" in snapshot.next):
            if result.get("messages"):
                for msg in result["messages"]:
                    if isinstance(msg, ToolMessage) and msg.name == "plan_route":
                        print(msg.content)
                        break
            return result

        if snapshot.next and "ask_for_images" in snapshot.next:
            user_response = input("Show destination images? (yes/no): ").strip().lower()

            final_result = None
            for event in graph.stream(
                Command(resume=user_response),
                config,
                stream_mode="values",
            ):
                final_result = event

            if user_response in {"yes", "y", "ok", "okay"}:
                if final_result and final_result.get("messages"):
                    for msg in final_result["messages"]:
                        if isinstance(msg, ToolMessage) and msg.name == "search_images":
                            print(msg.content)
                            break

            return final_result

        display_results(result)
        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def interactive_mode():
    while True:
        user_query = input("Query: ").strip()
        if user_query.lower() in {"quit", "exit"}:
            break

        if not user_query:
            continue

        pdf_path = input("PDF path (optional): ").strip()
        pdf_path = pdf_path if pdf_path and os.path.exists(pdf_path) else None

        run_travel_planner(user_query, pdf_path)


if __name__ == "__main__":
    import sys

    try:
        create_travel_workflow()
    except Exception as e:
        print(f"Error displaying graph: {e}")

    if len(sys.argv) > 1:
        query = sys.argv[1]
        pdf = sys.argv[2] if len(sys.argv) > 2 else None
        run_travel_planner(query, pdf)
    else:
        interactive_mode()
