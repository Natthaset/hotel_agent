from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# API Request / Response schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The message from the user")
    thread_id: Optional[str] = Field(default="default-session", description="Conversation session ID")

class ChatStreamChunk(BaseModel):
    token: str = ""
    event: Literal["token", "room_cards", "booking_confirmation", "error", "done"] = "token"
    data: Optional[dict] = None

class NewKnowledgeDocument(BaseModel):
    title: str = Field(..., min_length=2, description="Document or policy title")
    content: str = Field(..., min_length=5, description="Document body content to embed")

class SearchKnowledgeQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of nearest matches to return")

class FileExtractionRequest(BaseModel):
    filename: str = Field(..., min_length=1, description="Uploaded file name with extension")
    file_base64: str = Field(..., min_length=10, description="Base64 encoded file data")

class FileUploadKnowledgeRequest(BaseModel):
    filename: str = Field(..., min_length=1, description="Uploaded file name with extension")
    file_base64: str = Field(..., min_length=10, description="Base64 encoded file data")
    title: Optional[str] = Field(None, description="Optional custom title. If omitted, generated from filename.")

# Structured Output / Extraction schemas for LLM
class IntentClassification(BaseModel):
    intent: Literal["hotel_policy_inquiry", "room_availability", "create_booking", "general_chat"] = Field(
        ...,
        description="The primary user intent: hotel_policy_inquiry for general rules/amenities/cancellations, room_availability for checking available rooms, create_booking for placing a reservation, general_chat for greetings/thanks."
    )
    reasoning: str = Field(..., description="Brief reasoning for this classification")

class RoomAvailabilityExtraction(BaseModel):
    check_in: Optional[str] = Field(None, description="Check-in date formatted as YYYY-MM-DD")
    check_out: Optional[str] = Field(None, description="Check-out date formatted as YYYY-MM-DD")
    room_type: Optional[str] = Field(None, description="Requested room type or keywords like King, Suite, Villa")

class BookingReservationExtraction(BaseModel):
    customer_name: str = Field(..., description="Full name of guest")
    check_in_date: str = Field(..., description="Check-in date formatted as YYYY-MM-DD")
    check_out_date: str = Field(..., description="Check-out date formatted as YYYY-MM-DD")
    room_id: int = Field(..., description="Room ID number (1-5)")
    pax: int = Field(default=2, ge=1, le=10, description="Number of adult guests")

# Models returned by .NET API
class RoomInfo(BaseModel):
    id: int
    name: str
    type: str
    pricePerNight: float
    capacity: int
    description: str
    amenities: str
    isAvailable: bool = True

class BookingConfirmation(BaseModel):
    id: int
    customerName: str
    checkInDate: str
    checkOutDate: str
    roomId: int
    roomName: str
    roomType: str
    pax: int
    totalPrice: float
    totalNights: int
    status: str
    createdAt: str
