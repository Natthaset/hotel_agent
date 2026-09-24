import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from graph.nodes import router_node
from state import AgentState

@pytest.mark.asyncio
async def test_router_node_with_llm_policy_classification():
    # Arrange: LLM returns valid JSON classifying as hotel_policy_inquiry
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
        content=json.dumps({
            "intent": "hotel_policy_inquiry",
            "reasoning": "Guest is asking about breakfast and pool hours"
        })
    ))

    state: AgentState = {
        "messages": [HumanMessage(content="อาหารเช้าเริ่มกี่โมงครับ")],
        "intent": None,
        "intent_reasoning": None,
        "rag_context": None,
        "extracted_params": None,
        "tool_result": None,
        "room_cards": None,
        "booking_data": None,
        "error_message": None,
        "final_response": None
    }

    with patch("graph.nodes.get_llm", return_value=mock_llm):
        # Act
        result = await router_node(state)

        # Assert
        assert result["intent"] == "hotel_policy_inquiry"
        assert "breakfast" in result["intent_reasoning"].lower()

@pytest.mark.asyncio
async def test_router_node_with_llm_room_availability_classification():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
        content=json.dumps({
            "intent": "room_availability",
            "reasoning": "Guest wants to check rooms next weekend"
        })
    ))

    state: AgentState = {
        "messages": [HumanMessage(content="มีห้องว่างสุดสัปดาห์นี้ไหมครับ")],
        "intent": None,
        "intent_reasoning": None,
        "rag_context": None,
        "extracted_params": None,
        "tool_result": None,
        "room_cards": None,
        "booking_data": None,
        "error_message": None,
        "final_response": None
    }

    with patch("graph.nodes.get_llm", return_value=mock_llm):
        result = await router_node(state)
        assert result["intent"] == "room_availability"

@pytest.mark.asyncio
@pytest.mark.parametrize("user_msg, expected_intent", [
    ("ช่วยจองห้องพัก Pool Villa ให้หน่อยครับ", "create_booking"),
    ("มีห้องว่างไหมครับช่วงสิ้นเดือน", "room_availability"),
    ("สระว่ายน้ำเปิดกี่โมงและปิดกี่โมง", "hotel_policy_inquiry"),
    ("สวัสดีครับ ขอต้อนรับอย่างไรบ้าง", "general_chat")
])
async def test_router_node_keyword_fallback_when_llm_fails(user_msg, expected_intent):
    # Arrange: LLM raises exception (simulating timeout or unparseable output)
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Ollama connection failed"))

    state: AgentState = {
        "messages": [HumanMessage(content=user_msg)],
        "intent": None,
        "intent_reasoning": None,
        "rag_context": None,
        "extracted_params": None,
        "tool_result": None,
        "room_cards": None,
        "booking_data": None,
        "error_message": None,
        "final_response": None
    }

    with patch("graph.nodes.get_llm", return_value=mock_llm):
        # Act
        result = await router_node(state)

        # Assert: Keyword heuristic fallback takes over
        assert result["intent"] == expected_intent
        assert result["intent_reasoning"] == "Keyword fallback"

@pytest.mark.asyncio
async def test_router_node_with_list_content_response():
    # Arrange: LLM returns content as a list of text blocks (multimodal / content blocks)
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
        content=[{"type": "text", "text": json.dumps({
            "intent": "create_booking",
            "reasoning": "Guest wants to make a booking"
        })}]
    ))

    state: AgentState = {
        "messages": [HumanMessage(content=[{"type": "text", "text": "อยากจองห้องพักครับ"}])],
        "intent": None,
        "intent_reasoning": None,
        "rag_context": None,
        "extracted_params": None,
        "tool_result": None,
        "room_cards": None,
        "booking_data": None,
        "error_message": None,
        "final_response": None
    }

    with patch("graph.nodes.get_llm", return_value=mock_llm):
        result = await router_node(state)
        assert result["intent"] == "create_booking"
        assert "booking" in result["intent_reasoning"].lower()
