import uuid
import logging

from fastapi import FastAPI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis import RedisSaver

from agent import (
    WorkflowState,
    initialize_agent,
    decompose_query_node,
    check_cache_node,
    research_node,
    evaluate_quality_node,
    synthesize_response_node,
    route_after_cache_check,
    route_after_quality_evaluation,
)
from agent import launch_demo
from cache.wrapper import SemanticCacheWrapper
from cache.config import config

logger = logging.getLogger("agentic-workflow")

def _setup_memory(redis_url: str = None):
    """
    Setup the memory for the agent. If redis_url is provided, use Redis as the backend.
    Otherwise, use in-memory storage.
    """
    if redis_url:
        store = RedisSaver(redis_url=redis_url)
        store.setup()
        return store
    return InMemorySaver()
    
def _build_agent():
    workflow = StateGraph(WorkflowState)

    # Add nodes 
    workflow.add_node("decompose_query", decompose_query_node)
    workflow.add_node("check_cache", check_cache_node)
    workflow.add_node("research", research_node)
    workflow.add_node("evaluate_quality", evaluate_quality_node)
    workflow.add_node("synthesize", synthesize_response_node)

    # Set entry point to decomposition node
    workflow.set_entry_point("decompose_query")

    # Add edges
    workflow.add_edge("decompose_query", "check_cache")
    workflow.add_conditional_edges(
        "check_cache",
        route_after_cache_check,
        {
            "research": "research",  # Go to research if cache misses
            "synthesize": "synthesize",  # Skip to synthesis if all cached
        },
    )
    workflow.add_edge("research", "evaluate_quality")
    workflow.add_conditional_edges(
        "evaluate_quality",
        route_after_quality_evaluation,
        {
            "research": "research",
            "synthesize": "synthesize",
        },
    )
    workflow.add_edge("synthesize", END)

    memory_store = _setup_memory(redis_url=config.get("redis_url"))
    logger.info(f"Memory store initialized: {type(memory_store).__name__}")

    workflow_app = workflow.compile(checkpointer=memory_store)
    return workflow_app

def read_root():
    return {"message": "Hello, World!"}

def launch_app(config: dict = None, thread_id: str = ''):
    """
    Launch the research UI application.
    """
    cache = SemanticCacheWrapper.from_config(config)
    agent = _build_agent()
    print(f"🚀 Launching research UI with conversation thread ID: {thread_id}")

    try:
        launch_demo(agent, 
                    cache,
                    thread_id=thread_id,
                    share=True,
                    height=1500,
                    inline=True)
        print("✅ Research UI launched successfully")
        config = {
                "configurable": {
                    "thread_id": thread_id
                }
        }
        history = agent.get_state_history(config=config)
        print(f"🔄 Execution History: {[state for state in history]}")
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    thread_id = "testing_thread_1"
    launch_app(config=config,thread_id=thread_id)