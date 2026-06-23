from __future__ import annotations

from urllib.parse import quote

import httpx


class RetrievalClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=30.0)

    def dispatch(self, job: dict[str, object]) -> None:
        action = job["action"]
        collection = str(job["collection"])
        document_id = str(job.get("document_id") or "")
        if action in {"upsert", "rebuild"}:
            self._ensure_collection(collection)
        if action == "upsert":
            response = self.client.post(f"{self.base_url}/v1/documents/upsert", json=job["payload"])
        elif action == "archive":
            response = self.client.post(self._document_url(collection, document_id, "archive"))
        elif action == "restore":
            response = self.client.post(self._document_url(collection, document_id, "restore"))
        elif action == "delete":
            response = self.client.delete(self._document_url(collection, document_id))
        elif action == "rebuild":
            response = self.client.post(
                f"{self.base_url}/v1/index/rebuild-collection",
                json=job["payload"],
            )
        else:
            raise ValueError(f"Unsupported sync action: {action}")
        response.raise_for_status()

    def close(self) -> None:
        self.client.close()

    def _ensure_collection(self, collection: str) -> None:
        response = self.client.post(
            f"{self.base_url}/v1/collections",
            json={
                "name": collection,
                "description": "200iq mistake case collection",
                "chunk_strategy": "markdown_semantic",
            },
        )
        response.raise_for_status()

    def _document_url(self, collection: str, document_id: str, suffix: str = "") -> str:
        path = f"{self.base_url}/v1/documents/{quote(collection, safe='')}/{quote(document_id, safe='')}"
        return f"{path}/{suffix}" if suffix else path
