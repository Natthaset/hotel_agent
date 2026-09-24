import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from graph.nodes import response_generator_node
from state import AgentState

@pytest.mark.asyncio
async def test_response_generator_sanitizes_placeholder_name():
    # Arrange: LLM hallucinating placeholder name
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
        content="ยินดีต้อนรับค่ะ ดิฉัน [ชื่อของคุณ] ผู้ช่วยระดับ 5 ดาว มีอะไรให้รับใช้คะ"
    ))

    state: AgentState = {
        "messages": [HumanMessage(content="สวัสดีครับ")],
        "intent": "general_chat",
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
        result = await response_generator_node(state)

        # Assert
        assert "[ชื่อของคุณ]" not in result["final_response"]
        assert "Aura" in result["final_response"]
        assert "ดิฉัน Aura ผู้ช่วยระดับ 5 ดาว" in result["final_response"]

@pytest.mark.asyncio
async def test_response_generator_sanitizes_english_placeholder():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
        content="Best regards,\n[Your Name]\nExecutive Concierge"
    ))

    state: AgentState = {
        "messages": [HumanMessage(content="Thank you")],
        "intent": "general_chat",
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
        result = await response_generator_node(state)
        assert "[Your Name]" not in result["final_response"]
        assert "Aura" in result["final_response"]
