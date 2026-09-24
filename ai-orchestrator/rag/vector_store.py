import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from config import settings

logger = logging.getLogger("ai_orchestrator.rag")

class PolicyVectorStore:
    def __init__(self):
        self.client: QdrantClient | None = None
        self.embedder: TextEmbedding | None = None
        self.collection_name = settings.qdrant_collection
        self.embedding_model = settings.embedding_model

    def get_client(self) -> QdrantClient:
        if self.client is None:
            logger.info("Connecting to Qdrant at %s:%s with FastEmbed model %s",
                        settings.qdrant_host, settings.qdrant_port, self.embedding_model)
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=10
            )
        return self.client

    def get_embedder(self) -> TextEmbedding:
        if self.embedder is None:
            self.embedder = TextEmbedding(self.embedding_model)
        return self.embedder

    def ensure_collection(self, client: QdrantClient) -> None:
        try:
            collections = client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info("Creating Qdrant collection '%s' (dim: 384, distance: Cosine)...", self.collection_name)
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                )
        except Exception as ex:
            logger.error("Failed to ensure collection exists: %s", ex)

    def seed_policies_if_needed(self) -> None:
        """
        Idempotent startup task: Seeds hotel policy documents into Qdrant collection
        if the collection does not yet exist or is empty.
        """
        try:
            client = self.get_client()
            self.ensure_collection(client)

            count = client.count(self.collection_name).count
            if count > 0:
                logger.info("Qdrant collection '%s' already seeded with %d documents.", self.collection_name, count)
                return

            # Read policies data
            data_path = Path(__file__).parent.parent / "data" / "hotel_policies.json"
            if not data_path.exists():
                logger.warning("Policy file not found at %s. Skipping auto-seeding.", data_path)
                return

            with open(data_path, "r", encoding="utf-8") as f:
                policies: List[Dict[str, Any]] = json.load(f)

            embedder = self.get_embedder()
            doc_texts = [f"{p['title']}: {p['content']}" for p in policies]
            embeddings = list(embedder.embed(doc_texts))

            points = []
            for i, p in enumerate(policies):
                points.append(
                    models.PointStruct(
                        id=i + 1,
                        vector=embeddings[i].tolist(),
                        payload={
                            "policy_id": p["id"],
                            "id": i + 1,
                            "title": p["title"],
                            "content": p["content"],
                            "document": doc_texts[i]
                        }
                    )
                )

            logger.info("Seeding %d hotel policy documents into Qdrant '%s' via FastEmbed...", len(points), self.collection_name)
            client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info("Successfully seeded hotel policies into Qdrant.")
        except Exception as ex:
            logger.error("Error during Qdrant policy seeding: %s", ex, exc_info=True)

    def search_policies(self, query: str, top_k: int = 2) -> str:
        """
        Vector search for relevant hotel policies based on user query.
        """
        try:
            client = self.get_client()
            self.ensure_collection(client)
            embedder = self.get_embedder()

            query_vector = list(embedder.embed([query]))[0].tolist()
            results = client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k
            ).points

            if not results:
                return "No specific hotel policy document found matching the query."

            passages = []
            for r in results:
                payload = r.payload or {}
                doc_text = payload.get("document", "") or payload.get("content", "")
                passages.append(doc_text)

            return "\n\n---\n\n".join(passages)
        except Exception as ex:
            logger.error("Vector search failed in Qdrant: %s", ex)
            return "Unable to retrieve policy documents at this moment."

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Retrieve all embedded documents in the Qdrant collection.
        """
        try:
            client = self.get_client()
            self.ensure_collection(client)
            points, _ = client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            docs = []
            for pt in points:
                payload = pt.payload or {}
                doc_text = payload.get("document", "")
                title = payload.get("title", f"Document #{pt.id}")
                content = payload.get("content", doc_text)
                docs.append({
                    "id": pt.id,
                    "title": title,
                    "content": content,
                    "full_document": doc_text
                })
            return docs
        except Exception as ex:
            logger.error("Failed to scroll documents in Qdrant: %s", ex)
            return []

    def add_document(self, title: str, content: str) -> Dict[str, Any]:
        """
        Embed and upsert a new policy document into Qdrant using FastEmbed.
        """
        client = self.get_client()
        self.ensure_collection(client)
        embedder = self.get_embedder()

        full_text = f"{title.strip()}: {content.strip()}"
        
        # Determine next ID
        try:
            count = client.count(self.collection_name).count
            next_id = count + 100 + int(Path(__file__).stat().st_mtime % 1000)
        except Exception:
            import time
            next_id = int(time.time() % 100000)

        vector = list(embedder.embed([full_text]))[0].tolist()

        payload = {
            "id": next_id,
            "title": title.strip(),
            "content": content.strip(),
            "document": full_text
        }

        logger.info("Embedding new document [ID %d]: '%s' into Qdrant...", next_id, title)
        client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=next_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

        return {
            "id": next_id,
            "title": title.strip(),
            "content": content.strip(),
            "full_document": full_text
        }

    def delete_document(self, doc_id: int) -> bool:
        """
        Delete a document vector point from Qdrant by its numeric ID.
        """
        try:
            client = self.get_client()
            client.delete(
                collection_name=self.collection_name,
                points_selector=[doc_id]
            )
            logger.info("Deleted document point %d from Qdrant '%s'", doc_id, self.collection_name)
            return True
        except Exception as ex:
            logger.error("Failed to delete document %d from Qdrant: %s", doc_id, ex)
            return False

    def reindex_all_defaults(self) -> int:
        """
        Purges and re-indexes all default hotel policies from JSON into Qdrant.
        """
        client = self.get_client()
        data_path = Path(__file__).parent.parent / "data" / "hotel_policies.json"
        if not data_path.exists():
            return 0

        with open(data_path, "r", encoding="utf-8") as f:
            policies: List[Dict[str, Any]] = json.load(f)

        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.ensure_collection(client)
        embedder = self.get_embedder()
        doc_texts = [f"{p['title']}: {p['content']}" for p in policies]
        embeddings = list(embedder.embed(doc_texts))

        points = [
            models.PointStruct(
                id=i + 1,
                vector=embeddings[i].tolist(),
                payload={
                    "policy_id": p["id"],
                    "id": i + 1,
                    "title": p["title"],
                    "content": p["content"],
                    "document": doc_texts[i]
                }
            )
            for i, p in enumerate(policies)
        ]

        client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return len(policies)

    def test_search_detailed(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Test vector similarity search query and return matching documents with similarity scores.
        """
        try:
            client = self.get_client()
            self.ensure_collection(client)
            embedder = self.get_embedder()

            query_vector = list(embedder.embed([query]))[0].tolist()
            results = client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k
            ).points

            matches = []
            for r in results:
                payload = r.payload or {}
                doc_text = payload.get("document", "") or payload.get("content", "")
                title = payload.get("title", f"Result #{r.id}")
                score = getattr(r, "score", 0.0) or 0.0
                matches.append({
                    "id": r.id,
                    "score": round(float(score), 4),
                    "title": title,
                    "document": doc_text
                })
            return matches
        except Exception as ex:
            logger.error("Error in test_search_detailed: %s", ex)
            return []

policy_store = PolicyVectorStore()
