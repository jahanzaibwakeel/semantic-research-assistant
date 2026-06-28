import uuid
from typing import Any

from langchain_core.documents import Document as LCDocument
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams

from app.core.config import get_settings
from app.core.tracing import traced_span
from app.services.ai import get_embeddings


class QdrantStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = QdrantClient(url=self.settings.qdrant_url)
        self.embeddings = get_embeddings()

    def ensure_collection(self) -> None:
        with traced_span("qdrant.ensure_collection", collection=self.settings.qdrant_collection):
            collections = self.client.get_collections().collections
            if any(item.name == self.settings.qdrant_collection for item in collections):
                return
            vector_size = len(self.embeddings.embed_query("dimension probe"))
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert_documents(self, chunks: list[LCDocument]) -> None:
        self.ensure_collection()
        with traced_span("embedding.embed_documents", chunk_count=len(chunks)):
            vectors = self.embeddings.embed_documents([chunk.page_content for chunk in chunks])
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            metadata: dict[str, Any] = dict(chunk.metadata)
            metadata["text"] = chunk.page_content
            points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=metadata))
        if points:
            with traced_span("qdrant.upsert", collection=self.settings.qdrant_collection, point_count=len(points)):
                self.client.upsert(collection_name=self.settings.qdrant_collection, points=points)

    def search(
        self,
        query: str,
        owner_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        document_type: str | None = None,
        limit: int = 8,
    ):
        self.ensure_collection()
        query_filter = self._payload_filter(owner_id, document_id, project_id, document_type)
        with traced_span("embedding.embed_query", query_length=len(query)):
            query_vector = self.embeddings.embed_query(query)
        with traced_span("qdrant.search", collection=self.settings.qdrant_collection, limit=limit):
            return self.client.search(
                collection_name=self.settings.qdrant_collection,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )

    def scroll_payloads(
        self,
        owner_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        document_type: str | None = None,
        limit: int | None = None,
    ):
        self.ensure_collection()
        with traced_span("qdrant.scroll_payloads", collection=self.settings.qdrant_collection, limit=limit or self.settings.keyword_candidate_limit):
            points, _ = self.client.scroll(
                collection_name=self.settings.qdrant_collection,
                scroll_filter=self._payload_filter(owner_id, document_id, project_id, document_type),
                limit=limit or self.settings.keyword_candidate_limit,
                with_payload=True,
                with_vectors=False,
            )
        return points

    def delete_document(self, document_id: uuid.UUID) -> None:
        self.ensure_collection()
        with traced_span("qdrant.delete_document", collection=self.settings.qdrant_collection, document_id=str(document_id)):
            self.client.delete(
                collection_name=self.settings.qdrant_collection,
                points_selector=FilterSelector(filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
                )),
            )

    def update_document_metadata(
        self,
        document_id: uuid.UUID,
        project_id: uuid.UUID | None,
        tags: str | None,
    ) -> None:
        self.ensure_collection()
        with traced_span("qdrant.update_document_metadata", collection=self.settings.qdrant_collection, document_id=str(document_id)):
            self.client.set_payload(
                collection_name=self.settings.qdrant_collection,
                payload={
                    "project_id": str(project_id) if project_id else None,
                    "tags": tags,
                },
                points_selector=FilterSelector(filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
                )),
            )

    def _payload_filter(
        self,
        owner_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        document_type: str | None = None,
    ) -> Filter:
        must = [FieldCondition(key="owner_id", match=MatchValue(value=str(owner_id)))]
        if document_id:
            must.append(FieldCondition(key="document_id", match=MatchValue(value=str(document_id))))
        if project_id:
            must.append(FieldCondition(key="project_id", match=MatchValue(value=str(project_id))))
        if document_type:
            must.append(FieldCondition(key="document_type", match=MatchValue(value=document_type)))
        return Filter(must=must)
