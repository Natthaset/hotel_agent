import pytest
from graph.workflow import route_after_router
from state import AgentState

def test_route_after_router_branches():
    # 1. hotel_policy_inquiry -> rag
    state_rag: AgentState = {"intent": "hotel_policy_inquiry"} # type: ignore
    assert route_after_router(state_rag) == "rag"

    # 2. room_availability -> tool
    state_avail: AgentState = {"intent": "room_availability"} # type: ignore
    assert route_after_router(state_avail) == "tool"

    # 3. create_booking -> tool
    state_book: AgentState = {"intent": "create_booking"} # type: ignore
    assert route_after_router(state_book) == "tool"

    # 4. general_chat -> generator
    state_chat: AgentState = {"intent": "general_chat"} # type: ignore
    assert route_after_router(state_chat) == "generator"

    # 5. Fallback without intent -> generator
    state_empty: AgentState = {} # type: ignore
    assert route_after_router(state_empty) == "generator"
