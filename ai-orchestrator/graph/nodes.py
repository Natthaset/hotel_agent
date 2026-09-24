import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from config import settings
from state import AgentState
from rag.vector_store import policy_store
from tools.hotel_api_client import hotel_api
from schemas import IntentClassification, RoomAvailabilityExtraction, BookingReservationExtraction

logger = logging.getLogger("ai_orchestrator.graph.nodes")

def get_llm(temperature: float = 0.1, json_mode: bool = False) -> ChatOllama:
    kwargs: Dict[str, Any] = {
        "base_url": settings.ollama_base_url,
        "model": settings.ollama_model,
        "temperature": temperature,
        "keep_alive": settings.ollama_keep_alive,
    }
    if json_mode:
        kwargs["format"] = "json"
    return ChatOllama(**kwargs)

def extract_text_content(content: Any) -> str:
    """Safely extracts a string from message content, which may be a str or list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                parts.append(item["text"])
            elif isinstance(item, dict) and item.get("type") == "text" and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content or "")

# ------------------------------------------------------------------------------
# Node 1: Router (Intent Analysis)
# ------------------------------------------------------------------------------
async def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes user intent using the local LLM.
    Classifies into: hotel_policy_inquiry, room_availability, create_booking, or general_chat.
    """
    messages = state["messages"]
    last_user_msg = extract_text_content(messages[-1].content) if messages else ""

    system_prompt = (
        "You are an intent classification engine for Grand Azure Resort Concierge.\n"
        "Analyze the user's latest message and classify into EXACTLY ONE of the following intents:\n"
        "1. 'hotel_policy_inquiry': Asking about hotel rules, check-in/out hours, breakfast, swimming pool, spa, pet policy, smoking, cancellation, wifi, or amenities.\n"
        "2. 'room_availability': Asking to search or check available rooms, prices, room types, or dates.\n"
        "3. 'create_booking': Explicitly requesting to book, reserve, or confirm a reservation for a room.\n"
        "4. 'general_chat': Greetings, thank you, pleasantries, or general queries.\n\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "intent": "hotel_policy_inquiry" | "room_availability" | "create_booking" | "general_chat",\n'
        '  "reasoning": "short explanation"\n'
        "}"
    )

    try:
        llm = get_llm(temperature=0.0, json_mode=True)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Message: {last_user_msg}")
        ])
        parsed = json.loads(extract_text_content(response.content).strip())
        intent = parsed.get("intent", "general_chat")
        reasoning = parsed.get("reasoning", "")
        logger.info("Router classified intent: %s (Reason: %s)", intent, reasoning)
    except Exception as ex:
        logger.warning("Router intent parsing failed: %s. Defaulting to keyword heuristic.", ex)
        lowered = last_user_msg.lower()
        if any(w in lowered for w in ["จอง", "book", "reserve", "reservation"]):
            intent = "create_booking"
        elif any(w in lowered for w in ["ห้องว่าง", "availability", "available", "ราคาห้อง", "room", "พัก", "suite", "villa"]):
            intent = "room_availability"
        elif any(w in lowered for w in ["กี่โมง", "เวลา", "เช็คอิน", "อาหารเช้า", "สระว่ายน้ำ", "สัตว์เลี้ยง", "ยกเลิก", "policy", "pet", "breakfast", "pool", "cancel"]):
            intent = "hotel_policy_inquiry"
        else:
            intent = "general_chat"
        reasoning = "Keyword fallback"

    return {
        "intent": intent,
        "intent_reasoning": reasoning
    }

# ------------------------------------------------------------------------------
# Node 2: RAG (Hotel Policy Retrieval from Qdrant)
# ------------------------------------------------------------------------------
async def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Queries Qdrant vector database using FastEmbed for relevant hotel policies.
    Reformulates non-ASCII (e.g. Thai) queries into English keywords to match the English index.
    """
    messages = state["messages"]
    last_user_msg = extract_text_content(messages[-1].content) if messages else ""

    search_query = last_user_msg
    # If the user query contains Thai characters, translate/reformulate into English keywords
    if any(ord(char) > 127 for char in last_user_msg):
        try:
            llm = get_llm(temperature=0.0)
            system_p = (
                "Translate the following user question into English search keywords for hotel policy search.\n"
                "Example: 'เช็คอินกี่โมง' -> 'check in check out time'\n"
                "Example: 'อาหารเช้ามีที่ไหน' -> 'breakfast dining hours restaurant'\n"
                "Example: 'พาหมามาได้ไหม' -> 'pet dog policy guidelines fee'\n"
                "Example: 'ยกเลิกห้องได้ไหม' -> 'cancellation refund policy'\n"
                "Example: 'สูบบุหรี่ได้ไหม' -> 'smoking vaping regulations fee'\n"
                "Example: 'สระว่ายน้ำเปิดปิดกี่โมง' -> 'swimming pool gym spa operating hours'\n"
                "Output ONLY the English keywords, nothing else."
            )
            trans_res = await llm.ainvoke([
                SystemMessage(content=system_p),
                HumanMessage(content=last_user_msg)
            ])
            en_keywords = extract_text_content(trans_res.content).strip().strip('"').strip("'")
            if en_keywords and len(en_keywords) > 2:
                search_query = en_keywords
                logger.info("Reformulated query '%s' -> '%s'", last_user_msg, search_query)
        except Exception as ex:
            logger.warning("Query translation failed, falling back to original: %s", ex)

    logger.info("Executing RAG retrieval for query: '%s'", search_query)
    rag_context = policy_store.search_policies(search_query, top_k=2)
    return {"rag_context": rag_context}

# ------------------------------------------------------------------------------
# Node 3: Tool / API Calling Node (.NET 10 Web API)
# ------------------------------------------------------------------------------
async def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    Extracts structured parameters via LLM and executes requests to the .NET 10 API.
    Handles 400 Bad Request error codes gracefully.
    """
    intent = state.get("intent")
    messages = state["messages"]
    conversation_text = "\n".join([f"{m.type}: {extract_text_content(m.content)}" for m in messages[-4:]])
    # Use Thailand timezone (UTC+7) for Grand Azure Resort
    th_tz = timezone(timedelta(hours=7))
    today_str = datetime.now(th_tz).strftime("%Y-%m-%d")

    if intent == "room_availability":
        # Extract check-in, check-out, room_type
        extract_prompt = (
            f"Today's date is: {today_str}.\n"
            "Extract room search parameters from the conversation.\n"
            "Valid specific room types in this luxury resort are: 'Deluxe' (or 'Ocean King'), 'Suite' (or 'Executive'), 'Villa' (or 'Lagoon'), 'Family' (or 'Residence'), 'Penthouse' (or 'Royal').\n"
            "CRITICAL: If the user asks generally for room availability, room for rent, or does not specify a specific room category, 'room_type' MUST be null. Never use generic words like 'room', 'rental', 'rental room', 'hotel', 'เช่า' as room_type.\n"
            "Respond ONLY with a JSON object in this format:\n"
            "{\n"
            '  "check_in": "YYYY-MM-DD" or null,\n'
            '  "check_out": "YYYY-MM-DD" or null,\n'
            '  "room_type": "specific valid room category" or null\n'
            "}"
        )
        try:
            llm = get_llm(temperature=0.0, json_mode=True)
            res = await llm.ainvoke([
                SystemMessage(content=extract_prompt),
                HumanMessage(content=conversation_text)
            ])
            params = json.loads(extract_text_content(res.content).strip())
        except Exception:
            params = {"check_in": None, "check_out": None, "room_type": None}

        # Sanitize generic query terms from room_type
        generic_terms = {"room", "rental", "rental room", "hotel", "rooms", "ห้อง", "ห้องพัก", "ห้องเช่า", "เช่าห้อง", "พัก"}
        if params.get("room_type") and str(params["room_type"]).strip().lower() in generic_terms:
            params["room_type"] = None

        api_result = await hotel_api.get_room_availability(
            check_in=params.get("check_in"),
            check_out=params.get("check_out"),
            room_type=params.get("room_type")
        )

        room_cards = api_result.get("rooms", []) if api_result.get("success") else []
        error_msg = api_result.get("error") if not api_result.get("success") else None

        return {
            "extracted_params": params,
            "tool_result": api_result,
            "room_cards": room_cards,
            "error_message": error_msg
        }

    elif intent == "create_booking":
        # Extract reservation details: customer_name, check_in_date, check_out_date, room_id, pax
        extract_prompt = (
            f"Today's date is: {today_str}.\n"
            "Extract hotel room booking details from the conversation.\n"
            "Available Rooms: 1: Deluxe Ocean King (฿6,500), 2: Executive Panorama Suite (฿11,200), 3: Lagoon View Twin Villa (฿7,800), 4: Grand Azure Family Residence (฿14,500), 5: Royal Beachfront Penthouse (฿28,000).\n"
            "Respond ONLY with a JSON object in this format:\n"
            "{\n"
            '  "customer_name": "string" or null,\n'
            '  "check_in_date": "YYYY-MM-DD" or null,\n'
            '  "check_out_date": "YYYY-MM-DD" or null,\n'
            '  "room_id": integer (1-5) or null,\n'
            '  "pax": integer or 2\n'
            "}"
        )
        try:
            llm = get_llm(temperature=0.0, json_mode=True)
            res = await llm.ainvoke([
                SystemMessage(content=extract_prompt),
                HumanMessage(content=conversation_text)
            ])
            params = json.loads(extract_text_content(res.content).strip())
        except Exception:
            params = {}

        # Check if mandatory fields are missing
        missing = []
        if not params.get("customer_name"):
            missing.append("ชื่อผู้เข้าพัก (Customer Name)")
        if not params.get("check_in_date"):
            missing.append("วันเช็คอิน (Check-in Date)")
        if not params.get("check_out_date"):
            missing.append("วันเช็คเอาต์ (Check-out Date)")
        if not params.get("room_id"):
            missing.append("ประเภทหรือหมายเลขห้องพัก (Room Type/ID)")

        if missing:
            return {
                "extracted_params": params,
                "error_message": f"ต้องการข้อมูลเพิ่มเติมเพื่อยืนยันการจอง: {', '.join(missing)}",
                "tool_result": None,
                "booking_data": None
            }

        # Call .NET API to book
        api_result = await hotel_api.create_booking(
            customer_name=str(params["customer_name"]),
            check_in_date=str(params["check_in_date"]),
            check_out_date=str(params["check_out_date"]),
            room_id=int(params["room_id"]),
            pax=int(params.get("pax", 2))
        )

        booking_data = api_result.get("booking") if api_result.get("success") else None
        error_msg = api_result.get("error") if not api_result.get("success") else None

        return {
            "extracted_params": params,
            "tool_result": api_result,
            "booking_data": booking_data,
            "error_message": error_msg
        }

    return {}

# ------------------------------------------------------------------------------
# Node 4: Synthesizer / Response Generator Node
# ------------------------------------------------------------------------------
async def response_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Synthesizes the final luxury concierge response in Thai / English.
    Gracefully handles any 400 Bad Request error from .NET API with natural apologies.
    NEVER leaks internal tech stack names into the user-facing text.
    """
    intent = state.get("intent", "general_chat")
    rag_context = state.get("rag_context")
    tool_result = state.get("tool_result")
    error_message = state.get("error_message")
    booking_data = state.get("booking_data")
    room_cards = state.get("room_cards")
    messages = state["messages"]

    system_instruction = (
        "คุณคือ 'Aura' (ออร่า) เจ้าหน้าที่ Executive Concierge ระดับ 5 ดาว ของโรงแรมหรู Grand Azure Resort & Residences\n"
        "บุคลิกภาพ: สุภาพ นอบน้อม อบอุ่น สง่างาม และให้บริการระดับ First Class (ใช้คำลงท้าย 'ค่ะ')\n"
        "กฎเหล็ก:\n"
        "1. ห้ามเอ่ยถึงคำศัพท์เชิงเทคนิค เช่น '.NET', 'LangGraph', 'Qdrant', 'Ollama', 'API', 'JSON', 'HTTP 400', 'Database' หรือ 'Microservice' ในคำตอบเด็ดขาด\n"
        "2. หากระบบขัดข้องหรือเกิดข้อผิดพลาด (Error): ให้กล่าวขออภัยอย่างนอบน้อม แจ้งว่าระบบตรวจสอบห้องพักชั่วคราวขัดข้อง และขอให้ลูกค้าติดต่อแผนกต้อนรับหรือลองใหม่อีกครั้ง ห้ามกุเรื่อง แต่งเรื่อง หรือทึกทักเอาเองว่าตรวจสอบกับทีมงานแล้วมีห้องว่างเด็ดขาด หากไม่มีรายการห้องว่างในบริบทด้านล่าง ห้ามยืนยันว่ามีห้องว่างเด็ดขาด\n"
        "3. หากห้องพักไม่ว่าง (Fully Booked): ให้กล่าวขออภัยอย่างสุภาพ และแนะนำให้เลือกช่วงวันอื่น หรือเลือกประเภทห้องพักอื่นที่ว่าง\n"
        "4. กฎการให้ข้อมูลนโยบายและบริการโรงแรม (Strict Grounding & Anti-Hallucination):\n"
        "   - ให้อ้างอิงข้อเท็จจริงเฉพาะที่มีระบุอยู่ใน <hotel_policy_context> เท่านั้น\n"
        "   - ห้ามกุ คิดคำนวณ หรือคาดเดาตัวเลข ราคา อัตราค่าบริการ ระยะเวลา หรือเงื่อนไขที่ไม่มีระบุไว้ในบริบทโดยเด็ดขาด\n"
        "   - หากลูกค้าสอบถามข้อมูลที่ไม่มีในบริบท (เช่น สอบถามราคาหรือระยะเวลา แต่ในเอกสารมีเพียงชื่อบริการ): ให้ตอบเฉพาะข้อมูลที่มีอยู่จริง และแจ้งปฏิเสธเรื่องราคาอย่างสุภาพนอบน้อมว่า ในระบบยังไม่มีข้อมูลอัตราค่าบริการหรือรายละเอียดระบุไว้ และแนะนำให้ติดต่อสอบถามหรือสำรองบริการได้โดยตรงที่เคาน์เตอร์บริการหรือแผนกต้อนรับนะคะ\n"
        "   - หากลูกค้าสอบถามบริการที่โรงแรมไม่มีข้อมูลในบริบทเลย: ให้กล่าวขออภัยอย่างสุภาพ แจ้งว่าทางโรงแรมยังไม่มีข้อมูลบริการดังกล่าว และยินดีประสานงานหรือแนะนำบริการอื่นที่มีแทน\n"
        "5. หากเป็นการยืนยันการจองสำเร็จ: ให้แสดงความยินดี สรุปรายละเอียดการจอง (ชื่อผู้เข้าพัก, ห้องพัก, วันที่, จำนวนคืน, ยอดรวม) อย่างชัดเจนและสง่างาม\n"
        "6. กฎการระบุชื่อจริง (Strict Real Name Identity): ชื่อของคุณคือ 'Aura' (ออร่า) เท่านั้น ห้ามใช้ข้อความแทนชื่อหรือ Placeholder เช่น '[ชื่อของคุณ]', '[ชื่อคุณ]', '[Your Name]' หรือวงเล็บแทนชื่อใดๆ โดยเด็ดขาด หากต้องการแนะนำตัวหรือลงท้ายข้อความ ให้ใช้ชื่อจริงเสมอ เช่น 'Aura — Executive Concierge' หรือ 'ออร่า ผู้ช่วยระดับ 5 ดาว'\n"
    )

    context_prompt_parts = []

    if error_message:
        context_prompt_parts.append(f"สถานะระบบขัดข้อง: {error_message}\n(คำเตือน: ห้ามยืนยันว่ามีห้องว่างหรือแต่งเรื่องว่าทีมงานตรวจสอบแล้วเด็ดขาด ให้ขออภัยและแนะนำให้ติดต่อเจ้าหน้าที่หรือลองใหม่อีกครั้ง)")

    if rag_context:
        context_prompt_parts.append(f"ข้อมูลนโยบายโรงแรมจากระบบ:\n<hotel_policy_context>\n{rag_context}\n</hotel_policy_context>")

    if room_cards:
        rooms_summary = "\n".join([
            f"- ห้อง ID {r['id']}: {r['name']} ({r['type']}) | ราคา ฿{r['pricePerNight']:,.2f}/คืน | พักได้ {r['capacity']} ท่าน | จุดเด่น: {r.get('amenities', '')}"
            for r in room_cards
        ])
        context_prompt_parts.append(f"ห้องพักที่ว่างพร้อมให้บริการขณะนี้:\n{rooms_summary}")
    elif intent == "room_availability" and not error_message:
        context_prompt_parts.append("ผลการตรวจสอบห้องพัก: ไม่มีห้องว่างในช่วงวันที่หรือเงื่อนไขที่ระบุ (Fully Booked)")

    if booking_data:
        context_prompt_parts.append(
            f"ข้อมูลการจองที่ได้รับการยืนยันแล้ว:\n"
            f"หมายเลขการจอง: GA-{booking_data['id']:05d}\n"
            f"ชื่อผู้เข้าพัก: {booking_data['customerName']}\n"
            f"ห้องพัก: {booking_data['roomName']} ({booking_data['roomType']})\n"
            f"วันที่เข้าพัก: {booking_data['checkInDate'][:10]} ถึง {booking_data['checkOutDate'][:10]} ({booking_data['totalNights']} คืน)\n"
            f"จำนวนผู้เข้าพัก: {booking_data['pax']} ท่าน\n"
            f"ยอดรวม: ฿{booking_data['totalPrice']:,.2f}\n"
            f"สถานะ: {booking_data['status']}"
        )

    context_str = "\n\n".join(context_prompt_parts)
    full_system_instruction = system_instruction
    if context_str:
        full_system_instruction += f"\n\nบริบทข้อมูลอ้างอิงจากระบบสำหรับใช้ตอบคำถาม:\n{context_str}"

    llm = get_llm(temperature=0.1)
    response = await llm.ainvoke([
        SystemMessage(content=full_system_instruction),
        *messages
    ])

    final_text = extract_text_content(response.content).strip()

    # Bulletproof sanitization: แทนที่ placeholder เช่น [ชื่อของคุณ] ด้วยชื่อจริง Aura เสมอ
    placeholder_patterns = [
        "[ชื่อของคุณ]", "[ชื่อคุณ]", "[ชื่อผู้ช่วย]", "[ชื่อพนักงาน]", "[ชื่อเจ้าหน้าที่]",
        "[Your Name]", "[your name]", "[Name]"
    ]
    for ph in placeholder_patterns:
        final_text = final_text.replace(ph, "Aura")
    final_text = re.sub(r'\[(?:ชื่อของคุณ|ชื่อคุณ|ชื่อผู้ช่วย|ชื่อเจ้าหน้าที่|your name|name)\]', 'Aura', final_text, flags=re.IGNORECASE)

    return {
        "final_response": final_text,
        "messages": [AIMessage(content=final_text)]
    }
