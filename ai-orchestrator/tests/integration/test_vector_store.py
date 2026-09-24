import pytest
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

def test_fastembed_in_memory_qdrant_indexing_and_search():
    """
    Verifies that FastEmbed generates embeddings and Qdrant in-memory client
    performs semantic similarity search accurately without requiring external Docker services.
    """
    # Arrange: Isolated in-memory Qdrant client & FastEmbed ONNX
    client = QdrantClient(":memory:")
    embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
    collection_name = "test_policies"

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
    )

    docs = [
        "The breakfast buffet is served daily from 06:30 to 10:30 at Azure Ocean Breeze Restaurant.",
        "Our Olympic-size infinity pool is open to hotel guests daily from 06:00 to 20:00.",
        "Complimentary high-speed WiFi is available throughout the resort and in all guest rooms."
    ]

    embeddings = list(embedder.embed(docs))
    points = [
        models.PointStruct(
            id=i + 1,
            vector=embeddings[i].tolist(),
            payload={"id": i + 1, "document": docs[i]}
        )
        for i in range(len(docs))
    ]

    # Act: Upsert vectors
    client.upsert(collection_name=collection_name, points=points)

    # Assert count
    count_res = client.count(collection_name)
    assert count_res.count == 3

    # Act: Search using query vector
    query_text = "What time can I eat breakfast in the morning?"
    query_vector = list(embedder.embed([query_text]))[0].tolist()

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=1
    ).points

    # Assert: Top matched passage must be the breakfast document
    assert len(results) == 1
    top_doc = results[0].payload.get("document", "")
    assert "breakfast buffet" in top_doc.lower()
