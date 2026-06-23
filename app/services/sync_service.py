from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import Settings
from app.models import CaseRecord
from app.repositories.sync_job_repository import SyncJobRepository, now_iso
from app.services.retrieval_client import RetrievalClient
from app.services.retrieval_document_mapper import document_id_for_case, map_case_to_document


class SyncService:
    def __init__(self, repository: SyncJobRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def enqueue_case(self, case: CaseRecord, action: str) -> dict[str, object]:
        if not self.settings.sync_enabled:
            return {"enabled": False, "reason": "SYNC_ENABLED=false"}
        document_id = document_id_for_case(case.id)
        payload: dict[str, Any] = {}
        if action == "upsert":
            payload = {
                "collection": self.settings.retrieval_collection,
                "documents": [map_case_to_document(case)],
                "indexing": {"mode": "sync"},
            }
        else:
            payload = {
                "status": case.status.value,
                "updated_at": case.updated_at.isoformat(),
            }
        return self._enqueue(
            action=action,
            case_id=case.id,
            document_id=document_id,
            payload=payload,
        )

    def enqueue_rebuild(self, cases: list[CaseRecord]) -> dict[str, object]:
        if not self.settings.sync_enabled:
            return {"enabled": False, "reason": "SYNC_ENABLED=false"}
        payload = {
            "collection": self.settings.retrieval_collection,
            "documents": [map_case_to_document(case) for case in cases],
            "mode": "replace",
        }
        return self._enqueue("rebuild", None, None, payload)

    def process_due_jobs(self, retrieval: RetrievalClient) -> int:
        jobs = self.repository.claim_due_jobs(self.settings.sync_worker_batch_size)
        for job in jobs:
            try:
                retrieval.dispatch(job)
            except httpx.HTTPStatusError as exc:
                self._handle_failure(job, str(exc), exc.response.status_code)
            except Exception as exc:
                self._handle_failure(job, str(exc), None)
            else:
                self.repository.mark_succeeded(job["job_id"])
        return len(jobs)

    def retry_job(self, job_id: str) -> dict[str, object] | None:
        return self.repository.retry(job_id)

    def _enqueue(
        self,
        action: str,
        case_id: str | None,
        document_id: str | None,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        content_hash = _hash_value(payload)
        idempotency_key = ":".join(
            [
                "200iq-moments",
                self.settings.retrieval_collection,
                action,
                document_id or "collection",
                content_hash,
            ]
        )
        timestamp = now_iso()
        job, created = self.repository.create_job(
            {
                "job_id": f"sync_{uuid.uuid4().hex}",
                "source": "200iq-moments",
                "target": "retrieval-api",
                "collection": self.settings.retrieval_collection,
                "action": action,
                "case_id": case_id,
                "document_id": document_id,
                "idempotency_key": idempotency_key,
                "payload": payload,
                "status": "pending",
                "retry_count": 0,
                "max_retries": self.settings.sync_worker_max_retries,
                "created_at": timestamp,
                "updated_at": timestamp,
                "scheduled_at": timestamp,
            }
        )
        return {
            "enabled": True,
            "job_id": job["job_id"],
            "status": job["status"],
            "skipped": not created,
        }

    def _handle_failure(self, job: dict[str, Any], error: str, status_code: int | None) -> None:
        retries = int(job["retry_count"]) + 1
        is_client_error = status_code is not None and 400 <= status_code < 500
        if is_client_error or retries >= int(job["max_retries"]):
            self.repository.mark_failed(job["job_id"], retries, error)
            return
        delay = [5, 30, 120, 600, 1800][min(retries - 1, 4)]
        scheduled_at = (datetime.now().astimezone() + timedelta(seconds=delay)).isoformat()
        self.repository.schedule_retry(job["job_id"], retries, scheduled_at, error)


def _hash_value(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
