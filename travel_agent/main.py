import os
from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

from tools.calculate import calculate_budget
from tools.news import get_travel_news
from tools.pdf_extract import extract_from_pdf
from tools.weather import get_weather

load_dotenv()

tavily_search = TavilySearchResults(
    max_results=3,
    search_depth="basic",
    include_answer=True,
    include_raw_content=False,
    include_images=False,
)

class State(TypedDict):
    """State for the travel agent graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=2000,
)

system_message = """You are a helpful travel assistant. When you receive tool results, provide a clear and complete answer to the user's question. 

IMPORTANT: After using tools to gather information, you MUST provide a final answer to the user. Do not keep calling tools repeatedly. Synthesize the information from tool results and give a complete response."""


tools = [calculate_budget, get_travel_news, get_weather, extract_from_pdf, tavily_search]

llm_with_tools = llm.bind_tools(tools)


builder = StateGraph(State)

def tool_calling_llm(state: State):
    """Node that calls the LLM with tool binding."""
    messages = list(state["messages"])
    
    messages = [SystemMessage(content=system_message)] + messages
    
    return {"messages": [llm_with_tools.invoke(messages)]}


builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode(tools=tools))

builder.add_edge(START, "tool_calling_llm")
builder.add_conditional_edges(
    "tool_calling_llm",
    tools_condition
)
builder.add_edge("tools", "tool_calling_llm")

graph = builder.compile()



def run_interactive():
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit']:
            print("Goodbye! Happy travels!")
            break
        
        if not user_input:
            continue
        
        print("\nAssistant: ", end="", flush=True)
        
        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config={"recursion_limit": 50}
            )
            
            print(result['messages'][-1].content + "\n")
        except Exception as e:
            print(f"Error: {str(e)}\n")


if __name__ == "__main__":
   
    run_interactive()
    
    
    

