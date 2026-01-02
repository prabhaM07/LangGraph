"""
Langfuse integration for the Travel Planning System
This module provides observability and tracing for the multi-agent workflow
Compatible with Langfuse SDK v3
"""

import os
from typing import Any, Dict
from dotenv import load_dotenv
from langfuse import Langfuse, observe, get_client
from datetime import datetime

load_dotenv()

# Initialize Langfuse client
def get_langfuse_client():
    """Get Langfuse client with proper initialization"""
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
    )

langfuse = get_langfuse_client()


class TravelPlannerObserver:
    """Observability wrapper for the travel planning workflow"""
    
    def __init__(self):
        self.langfuse = get_client()
        self.current_trace = None
        self.trace_id = None
    
    def start_trace(self, user_query: str, pdf_path: str = None) -> Any:
        """Start a new trace for the travel planning session"""
        # In SDK v3, we use context manager approach
        context_manager = self.langfuse.start_as_current_span(
            name="travel-planning-session",
            input={
                "user_query": user_query,
                "pdf_path": pdf_path,
                "timestamp": datetime.now().isoformat()
            },
            metadata={
                "system": "multi-agent-travel-planner",
                "version": "1.0"
            }
        )
        # Enter the context and get the actual span
        self.current_trace = context_manager.__enter__()
        self.trace_id = getattr(self.current_trace, 'trace_id', 'unknown')
        return self.current_trace
    
    def log_agent_execution(self, agent_name: str, state: Dict, output: Any):
        """Log individual agent execution"""
        if not self.current_trace:
            return
        
        try:
            # Create a nested span
            context_manager = self.langfuse.start_as_current_span(
                name=f"agent-{agent_name}",
                input={
                    "agent": agent_name,
                    "state_summary": {
                        "user_query": state.get("user_query"),
                        "messages_count": len(state.get("messages", [])),
                        "task_complete": state.get("task_complete", False)
                    }
                },
                metadata={"agent_type": agent_name}
            )
            span = context_manager.__enter__()
            span.update(output={"result": str(output)[:500]})
            context_manager.__exit__(None, None, None)
            return span
        except Exception as e:
            print(f"Warning: Could not log agent execution: {e}")
            return None
    
    def log_tool_call(self, tool_name: str, tool_input: Dict, tool_output: Any):
        """Log tool execution"""
        if not self.current_trace:
            return
        
        try:
            context_manager = self.langfuse.start_as_current_generation(
                name=f"tool-{tool_name}",
                input=tool_input,
                metadata={
                    "tool_name": tool_name,
                    "tool_type": "external_api"
                }
            )
            generation = context_manager.__enter__()
            generation.update(output=tool_output)
            context_manager.__exit__(None, None, None)
            return generation
        except Exception as e:
            print(f"Warning: Could not log tool call: {e}")
            return None
    
    def log_llm_call(self, agent_name: str, prompt: str, response: str, 
                     model: str = "llama-3.1-8b-instant", tokens: Dict = None):
        """Log LLM generation"""
        if not self.current_trace:
            return
        
        try:
            context_manager = self.langfuse.start_as_current_generation(
                name=f"llm-{agent_name}",
                model=model,
                input={"prompt": prompt},
                metadata={
                    "agent": agent_name,
                    "model_provider": "groq"
                }
            )
            generation = context_manager.__enter__()
            
            update_params = {"output": response}
            if tokens:
                update_params["usage"] = {
                    "input": tokens.get("prompt_tokens", 0),
                    "output": tokens.get("completion_tokens", 0),
                    "total": tokens.get("total_tokens", 0)
                }
            
            generation.update(**update_params)
            context_manager.__exit__(None, None, None)
            return generation
        except Exception as e:
            print(f"Warning: Could not log LLM call: {e}")
            return None
    
    def log_human_review(self, summary: str, feedback: str):
        """Log human review checkpoint"""
        if not self.current_trace:
            return
        
        try:
            context_manager = self.langfuse.start_as_current_span(
                name="human-review-checkpoint",
                input={"summary": summary},
                metadata={"interaction_type": "human_in_the_loop"}
            )
            span = context_manager.__enter__()
            span.update(output={"feedback": feedback})
            context_manager.__exit__(None, None, None)
            return span
        except Exception as e:
            print(f"Warning: Could not log human review: {e}")
            return None
    
    def score_final_result(self, score_name: str, value: float, comment: str = None):
        """Add a score to the current trace"""
        if not self.current_trace:
            return
        
        try:
            self.current_trace.score(
                name=score_name,
                value=value,
                data_type="NUMERIC",
                comment=comment
            )
        except Exception as e:
            print(f"Warning: Could not add score: {e}")
    
    def end_trace(self, final_result: str, success: bool = True):
        """End the current trace"""
        if not self.current_trace:
            return
        
        try:
            self.current_trace.update(
                output={
                    "final_result": final_result[:1000],  # Truncate
                    "success": success
                },
                metadata={
                    "completion_time": datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Warning: Could not update trace: {e}")
        
        # Flush to ensure data is sent
        try:
            self.langfuse.flush()
        except Exception as e:
            print(f"Warning: Could not flush: {e}")
        
        self.current_trace = None
        self.trace_id = None


# Decorator-based approach for simple function tracing
@observe()
def traced_coordinator_node(state, llm):
    """Coordinator node with automatic tracing"""
    from agents import coordinator_node
    result = coordinator_node(state, llm)
    
    # Add metadata using the client
    langfuse = get_client()
    try:
        langfuse.update_current_span(
            metadata={"agent_type": "coordinator", "role": "routing"}
        )
    except:
        pass
    
    return result


@observe()
def traced_tool_execution(tool_func, *args, **kwargs):
    """Wrapper for tool execution with tracing"""
    result = tool_func(*args, **kwargs)
    
    # Add metadata using the client
    langfuse = get_client()
    try:
        langfuse.update_current_span(
            metadata={
                "tool_name": tool_func.__name__,
                "tool_type": "external_api"
            }
        )
    except:
        pass
    
    return result


# Example: Enhanced workflow with observability
def create_observed_workflow():
    """Create workflow with Langfuse observability"""
    from workflow import create_travel_workflow
    
    # Create base workflow
    graph = create_travel_workflow()
    
    # Note: You would wrap the graph execution in the main.py file
    # See the modified main.py example below
    
    return graph


# Helper function to wrap state updates
def observe_state_transition(observer: TravelPlannerObserver, 
                             from_node: str, 
                             to_node: str, 
                             state: Dict):
    """Log state transitions between nodes"""
    if observer.current_trace:
        try:
            context_manager = observer.langfuse.start_as_current_span(
                name=f"transition-{from_node}-to-{to_node}",
                input={"from": from_node, "to": to_node},
                metadata={"transition_type": "graph_edge"}
            )
            span = context_manager.__enter__()
            span.update(output={"state_keys": list(state.keys())})
            context_manager.__exit__(None, None, None)
        except Exception as e:
            print(f"Warning: Could not log transition: {e}")


# Alternative: Use context manager approach (v3 recommended way)
def trace_agent_execution(agent_name: str, state: Dict):
    """Context manager for tracing agent execution (v3 pattern)"""
    langfuse = get_client()
    return langfuse.start_as_current_span(
        name=f"agent-{agent_name}",
        input={
            "agent": agent_name,
            "user_query": state.get("user_query"),
            "messages_count": len(state.get("messages", []))
        },
        metadata={"agent_type": agent_name}
    )