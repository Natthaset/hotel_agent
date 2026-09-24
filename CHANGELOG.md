# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-24

### Added
- **Infrastructure:**
  - Microservices monorepo architecture with `docker-compose.yml` (`linux/arm64`).
  - MySQL 8.0 with automated healthcheck and persistent storage.
  - Qdrant vector database for semantic policy search.
  - Local Ollama LLM service optimized for Apple Silicon (8GB-10GB memory limit).
  - Model pulling utility (`scripts/pull-model.sh`) supporting Qwen2.5 7B.
- **Backend (.NET 10 Web API):**
  - Clean architecture with Controller, Service, and Repository layers.
  - Entity Framework Core with Pomelo MySQL provider.
  - Domain models: `Room` and `Booking`.
  - Database auto-migration and room seed data on startup.
  - Endpoints: `GET /api/v1/rooms/availability` and `POST /api/v1/bookings`.
- **AI Orchestrator (FastAPI + LangGraph):**
  - Multi-agent StateGraph with Intent Router, RAG Search, and Tool Calling nodes.
  - FastEmbed ONNX local embeddings (`BAAI/bge-small-en-v1.5`) with zero Ollama VRAM overhead.
  - Automatic hotel policy ingestion on startup into Qdrant.
  - Graceful error handling and natural apologies for API errors.
  - Server-Sent Events (SSE) `/chat` endpoint with multi-turn `thread_id` memory.
- **Frontend (SvelteKit + Svelte 5):**
  - Luxury 5-Star Grand Azure Resort & Concierge UI in Vanilla CSS.
  - Real-time SSE streaming consumption.
  - Quick prompt chips, dynamic room availability cards, and live concierge status.
