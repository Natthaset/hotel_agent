from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Classification & routing
    intent: Optional[str]
    intent_reasoning: Optional[str]
    
    # RAG knowledge
    rag_context: Optional[str]
    
    # Tool execution
    extracted_params: Optional[Dict[str, Any]]
    tool_result: Optional[Any]
    error_message: Optional[str]
    
    # UI Rich Payloads
    room_cards: Optional[List[Dict[str, Any]]]
    booking_data: Optional[Dict[str, Any]]
    
    # Final streamed response
    final_response: Optional[str]
