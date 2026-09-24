import pytest
from pydantic import ValidationError
from schemas import (
    ChatRequest,
    NewKnowledgeDocument,
    SearchKnowledgeQuery,
    IntentClassification,
    BookingReservationExtraction,
    RoomInfo,
    BookingConfirmation
)

def test_chat_request_valid():
    req = ChatRequest(message="ขอสอบถามห้องพักว่างครับ", thread_id="guest-123")
    assert req.message == "ขอสอบถามห้องพักว่างครับ"
    assert req.thread_id == "guest-123"

def test_chat_request_empty_message_raises_validation_error():
    with pytest.raises(ValidationError):
        ChatRequest(message="")

def test_new_knowledge_document_validation():
    doc = NewKnowledgeDocument(
        title="Check-in Policy",
        content="Standard check-in time is 15:00. Early check-in is subject to availability."
    )
    assert doc.title == "Check-in Policy"
    assert len(doc.content) > 5

    # Short title should fail
    with pytest.raises(ValidationError):
        NewKnowledgeDocument(title="A", content="Valid content here")

def test_search_knowledge_query_validation():
    query = SearchKnowledgeQuery(query="breakfast", top_k=5)
    assert query.top_k == 5

    with pytest.raises(ValidationError):
        SearchKnowledgeQuery(query="test", top_k=20)  # top_k max is 10

def test_intent_classification_schema():
    valid = IntentClassification(
        intent="hotel_policy_inquiry",
        reasoning="Guest asking about pet policy"
    )
    assert valid.intent == "hotel_policy_inquiry"

    with pytest.raises(ValidationError):
        IntentClassification(intent="unknown_intent", reasoning="Invalid")

def test_booking_reservation_extraction():
    booking = BookingReservationExtraction(
        customer_name="Somchai Jaidee",
        check_in_date="2026-10-01",
        check_out_date="2026-10-04",
        room_id=1,
        pax=2
    )
    assert booking.customer_name == "Somchai Jaidee"
    assert booking.room_id == 1
    assert booking.pax == 2

    # Pax > 10 should fail
    with pytest.raises(ValidationError):
        BookingReservationExtraction(
            customer_name="Large Group",
            check_in_date="2026-10-01",
            check_out_date="2026-10-04",
            room_id=1,
            pax=15
        )

def test_room_info_and_booking_confirmation():
    room = RoomInfo(
        id=1,
        name="Deluxe King",
        type="Deluxe",
        pricePerNight=6500.0,
        capacity=2,
        description="Luxury room",
        amenities="WiFi, Pool"
    )
    assert room.isAvailable is True

    confirmation = BookingConfirmation(
        id=101,
        customerName="Somchai",
        checkInDate="2026-10-01",
        checkOutDate="2026-10-03",
        roomId=1,
        roomName="Deluxe King",
        roomType="Deluxe",
        pax=2,
        totalPrice=13000.0,
        totalNights=2,
        status="Confirmed",
        createdAt="2026-09-24T12:00:00"
    )
    assert confirmation.totalPrice == 13000.0
    assert confirmation.totalNights == 2
