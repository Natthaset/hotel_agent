import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from graph.nodes import router_node, rag_node, tool_node, response_generator_node

logger = logging.getLogger("ai_orchestrator.graph.workflow")

def route_after_router(state: AgentState) -> Literal["rag", "tool", "generator"]:
    intent = state.get("intent", "general_chat")
    logger.info("Routing decision from router: intent='%s'", intent)
    if intent == "hotel_policy_inquiry":
        return "rag"
    elif intent in ("room_availability", "create_booking"):
        return "tool"
    else:
        return "generator"

def build_concierge_graph():
    """
    Builds the Multi-Agent StateGraph for the Grand Azure Concierge system.
    """
    graph_builder = StateGraph(AgentState)  # type: ignore[arg-type]

    # 1. Add Nodes
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("rag", rag_node)
    graph_builder.add_node("tool", tool_node)
    graph_builder.add_node("generator", response_generator_node)

    # 2. Add Edges & Conditional Routing
    graph_builder.add_edge(START, "router")

    graph_builder.add_conditional_edges(
        "router",
        route_after_router,
        {
            "rag": "rag",
            "tool": "tool",
            "generator": "generator"
        }
    )

    graph_builder.add_edge("rag", "generator")
    graph_builder.add_edge("tool", "generator")
    graph_builder.add_edge("generator", END)

    # 3. Compile with in-memory checkpointer for multi-turn thread persistence
    memory = MemorySaver()
    compiled_app = graph_builder.compile(checkpointer=memory)
    logger.info("LangGraph StateGraph compiled successfully with MemorySaver.")
    return compiled_app

concierge_graph = build_concierge_graph()
