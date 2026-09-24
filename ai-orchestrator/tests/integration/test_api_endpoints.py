import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Healthy"
        assert "AI.Orchestrator" in data["service"]

@pytest.mark.asyncio
async def test_chat_sync_endpoint():
    mock_final_state = {
        "intent": "general_chat",
        "final_response": "สวัสดีค่ะ ยินดีต้อนรับสู่ Grand Azure Resort & Residences มีอะไรให้ฉันช่วยดูแลวันนี้คะ?",
        "room_cards": [],
        "booking_data": None,
        "error_message": None
    }

    with patch("main.concierge_graph.ainvoke", new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.return_value = mock_final_state

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "message": "สวัสดีครับ",
                "thread_id": "session-101"
            }
            response = await client.post("/chat/sync", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["thread_id"] == "session-101"
            assert data["intent"] == "general_chat"
            assert "Grand Azure" in data["response"]

@pytest.mark.asyncio
async def test_knowledge_api_endpoints():
    mock_docs = [
        {"id": 1, "title": "Check-in Time", "content": "Check-in is at 15:00."}
    ]

    with patch("main.policy_store.get_all_documents", return_value=mock_docs), \
         patch("main.policy_store.add_document", return_value={"id": 2, "title": "Pool", "content": "Pool closes at 20:00"}), \
         patch("main.policy_store.delete_document", return_value=True), \
         patch("main.policy_store.test_search_detailed", return_value=[{"id": 1, "score": 0.88, "title": "Check-in Time"}]):

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. GET /api/v1/knowledge
            res_list = await client.get("/api/v1/knowledge")
            assert res_list.status_code == 200
            assert res_list.json()["count"] == 1

            # 2. POST /api/v1/knowledge
            new_doc = {"title": "Pool Policy", "content": "Pool closes at 20:00 every evening."}
            res_create = await client.post("/api/v1/knowledge", json=new_doc)
            assert res_create.status_code == 200
            assert res_create.json()["status"] == "success"

            # 3. POST /api/v1/knowledge/search
            search_body = {"query": "check in time", "top_k": 2}
            res_search = await client.post("/api/v1/knowledge/search", json=search_body)
            assert res_search.status_code == 200
            assert len(res_search.json()["matches"]) == 1

            # 4. DELETE /api/v1/knowledge/1
            res_del = await client.delete("/api/v1/knowledge/1")
            assert res_del.status_code == 200
            assert res_del.json()["status"] == "success"

@pytest.mark.asyncio
async def test_file_extraction_and_upload_endpoints():
    import base64
    sample_text = "Free valet parking is available 24/7."
    b64 = base64.b64encode(sample_text.encode("utf-8")).decode("utf-8")

    with patch("main.policy_store.add_document", return_value={"id": 99, "title": "Valet Parking Policy", "content": sample_text}):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test /api/v1/knowledge/extract-file
            res_extract = await client.post("/api/v1/knowledge/extract-file", json={
                "filename": "valet_parking_policy.txt",
                "file_base64": b64
            })
            assert res_extract.status_code == 200
            extract_data = res_extract.json()
            assert extract_data["status"] == "success"
            assert "Valet Parking" in extract_data["suggested_title"]
            assert "Free valet parking" in extract_data["content"]

            # 2. Test /api/v1/knowledge/upload-file
            res_upload = await client.post("/api/v1/knowledge/upload-file", json={
                "filename": "valet_parking_policy.txt",
                "file_base64": b64,
                "title": "VIP Valet Parking"
            })
            assert res_upload.status_code == 200
            upload_data = res_upload.json()
            assert upload_data["status"] == "success"
            assert "VIP Valet Parking" in upload_data["message"]
