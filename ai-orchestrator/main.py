import base64
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from config import settings
from schemas import (
    ChatRequest,
    NewKnowledgeDocument,
    SearchKnowledgeQuery,
    FileExtractionRequest,
    FileUploadKnowledgeRequest
)
from rag.vector_store import policy_store
from rag.file_parser import extract_file_content
from graph.workflow import concierge_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_orchestrator")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Orchestrator service on port %d...", settings.port)
    # Seed hotel policies into Qdrant on startup
    try:
        policy_store.seed_policies_if_needed()
    except Exception as ex:
        logger.warning("Initial policy seeding skipped or will retry: %s", ex)
    yield
    logger.info("Shutting down AI Orchestrator service.")

app = FastAPI(
    title="Intelligent Concierge AI Orchestrator",
    description="Multi-agent hotel concierge powered by LangGraph, Qdrant RAG, and .NET 10 API",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "Healthy",
        "service": "AI.Orchestrator.FastAPI.LangGraph",
        "ollama_model": settings.ollama_model,
        "qdrant_collection": settings.qdrant_collection
    }

async def chat_event_generator(req: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Executes LangGraph workflow and yields Server-Sent Events (SSE) to the client.
    """
    thread_id = req.thread_id or "default-session"
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {
        "messages": [HumanMessage(content=req.message)]
    }

    try:
        # Execute the compiled LangGraph workflow
        final_state = await concierge_graph.ainvoke(input_data, config=config)

        # 1. Send room cards event if rooms were found
        room_cards = final_state.get("room_cards")
        if room_cards:
            yield json.dumps({
                "event": "room_cards",
                "data": room_cards
            })

        # 2. Send booking confirmation event if a booking was made
        booking_data = final_state.get("booking_data")
        if booking_data:
            yield json.dumps({
                "event": "booking_confirmation",
                "data": booking_data
            })

        # 3. Stream response text in progressive chunks for typing animation
        final_response = final_state.get("final_response", "")
        # Break into words/tokens for progressive streaming
        words = final_response.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield json.dumps({
                "event": "token",
                "token": chunk
            })

        # 4. Completion event
        yield json.dumps({
            "event": "done",
            "thread_id": thread_id,
            "intent": final_state.get("intent")
        })

    except Exception as ex:
        logger.error("Error during LangGraph streaming execution: %s", ex, exc_info=True)
        yield json.dumps({
            "event": "error",
            "error": "ขออภัยเป็นอย่างยิ่งค่ะ ระบบผู้ช่วยอัจฉริยะขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งนะคะ"
        })

@app.post("/chat")
async def chat_sse(request: Request, body: ChatRequest):
    """
    Exposes POST /chat returning Server-Sent Events (SSE) for streaming text and rich cards.
    """
    return EventSourceResponse(
        chat_event_generator(body),
        media_type="text/event-stream"
    )

@app.post("/chat/sync")
async def chat_sync(body: ChatRequest):
    """
    Synchronous fallback endpoint returning the full completed response at once.
    """
    thread_id = body.thread_id or "default-session"
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {
        "messages": [HumanMessage(content=body.message)]
    }

    try:
        final_state = await concierge_graph.ainvoke(input_data, config=config)
        return {
            "thread_id": thread_id,
            "intent": final_state.get("intent"),
            "response": final_state.get("final_response", ""),
            "room_cards": final_state.get("room_cards", []),
            "booking_data": final_state.get("booking_data"),
            "error": final_state.get("error_message")
        }
    except Exception as ex:
        logger.error("Error in sync chat: %s", ex, exc_info=True)
        raise HTTPException(status_code=500, detail=str(ex))

# ==============================================================================
# Knowledge Base & Vector Embedding Management Endpoints
# ==============================================================================

@app.get("/api/v1/knowledge")
async def list_knowledge():
    """
    List all documents currently embedded and stored in Qdrant collection.
    """
    docs = policy_store.get_all_documents()
    return {
        "status": "success",
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "count": len(docs),
        "documents": docs
    }

@app.post("/api/v1/knowledge")
async def create_and_embed_knowledge(doc: NewKnowledgeDocument):
    """
    Embed a new policy document with FastEmbed and upsert it into Qdrant.
    """
    result = policy_store.add_document(title=doc.title, content=doc.content)
    return {
        "status": "success",
        "message": f"Successfully embedded and indexed document '{doc.title}' into Qdrant vector database.",
        "document": result
    }

@app.post("/api/v1/knowledge/extract-file")
async def extract_knowledge_file(body: FileExtractionRequest):
    """
    Extracts text content and generates a suggested title from an uploaded document
    (PDF, Image, Word .docx, Excel .xlsx, CSV, or Text).
    """
    try:
        raw_b64 = body.file_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        file_bytes = base64.b64decode(raw_b64)
        content, suggested_title = extract_file_content(body.filename, file_bytes)
        return {
            "status": "success",
            "filename": body.filename,
            "suggested_title": suggested_title,
            "content": content,
            "size_bytes": len(file_bytes)
        }
    except Exception as ex:
        logger.error("Failed to extract content from file %s: %s", body.filename, ex, exc_info=True)
        raise HTTPException(status_code=400, detail=str(ex))

@app.post("/api/v1/knowledge/upload-file")
async def upload_and_embed_knowledge_file(body: FileUploadKnowledgeRequest):
    """
    Extracts text from uploaded file, creates FastEmbed vector embeddings, and stores in Qdrant.
    """
    try:
        raw_b64 = body.file_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        file_bytes = base64.b64decode(raw_b64)
        content, auto_title = extract_file_content(body.filename, file_bytes)
        final_title = (body.title or "").strip() or auto_title

        result = policy_store.add_document(title=final_title, content=content)
        return {
            "status": "success",
            "message": f"Successfully extracted, embedded, and indexed '{final_title}' from file '{body.filename}' into Qdrant.",
            "document": result
        }
    except Exception as ex:
        logger.error("Failed to upload and embed file %s: %s", body.filename, ex, exc_info=True)
        raise HTTPException(status_code=400, detail=str(ex))

@app.delete("/api/v1/knowledge/{doc_id}")
async def delete_knowledge(doc_id: int):
    """
    Delete a document vector point from Qdrant by its point ID.
    """
    success = policy_store.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document point ID {doc_id} not found or could not be deleted.")
    return {"status": "success", "message": f"Document point ID {doc_id} deleted from vector store."}

@app.post("/api/v1/knowledge/reindex")
async def reindex_knowledge():
    """
    Reset and re-index all default hotel policy documents into Qdrant.
    """
    count = policy_store.reindex_all_defaults()
    return {"status": "success", "message": f"Successfully re-indexed {count} policy documents into Qdrant."}

@app.post("/api/v1/knowledge/search")
async def search_knowledge(body: SearchKnowledgeQuery):
    """
    Interactive test vector search: queries Qdrant with FastEmbed and returns matched passages with similarity scores.
    """
    matches = policy_store.test_search_detailed(query=body.query, top_k=body.top_k)
    return {
        "query": body.query,
        "matches_count": len(matches),
        "matches": matches
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
