from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class SyncJobRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sync_jobs (
                  job_id TEXT PRIMARY KEY,
                  source TEXT NOT NULL,
                  target TEXT NOT NULL,
                  collection TEXT NOT NULL,
                  action TEXT NOT NULL,
                  case_id TEXT,
                  document_id TEXT,
                  idempotency_key TEXT NOT NULL UNIQUE,
                  payload_json TEXT NOT NULL,
                  status TEXT NOT NULL,
                  retry_count INTEGER NOT NULL DEFAULT 0,
                  max_retries INTEGER NOT NULL DEFAULT 5,
                  last_error TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  scheduled_at TEXT NOT NULL,
                  started_at TEXT,
                  finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sync_job_events (
                  event_id TEXT PRIMARY KEY,
                  job_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  message TEXT,
                  data_json TEXT,
                  created_at TEXT NOT NULL
                );
                """
            )

    def create_job(self, job: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = self.get_by_idempotency_key(job["idempotency_key"])
        if existing:
            return existing, False
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_jobs (
                  job_id, source, target, collection, action, case_id, document_id,
                  idempotency_key, payload_json, status, retry_count, max_retries,
                  last_error, created_at, updated_at, scheduled_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job["source"],
                    job["target"],
                    job["collection"],
                    job["action"],
                    job.get("case_id"),
                    job.get("document_id"),
                    job["idempotency_key"],
                    json.dumps(job["payload"], ensure_ascii=False, sort_keys=True),
                    job["status"],
                    job["retry_count"],
                    job["max_retries"],
                    job.get("last_error"),
                    job["created_at"],
                    job["updated_at"],
                    job["scheduled_at"],
                    job.get("started_at"),
                    job.get("finished_at"),
                ),
            )
        self.add_event(job["job_id"], "created")
        return self.get(job["job_id"]), True

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sync_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._decode(row) if row else None

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sync_jobs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return self._decode(row) if row else None

    def list_jobs(
        self,
        collection: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM sync_jobs WHERE 1=1"
        params: list[Any] = []
        if collection:
            sql += " AND collection = ?"
            params.append(collection)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._decode(row) for row in rows]

    def claim_due_jobs(self, limit: int) -> list[dict[str, Any]]:
        now = now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sync_jobs
                WHERE status IN ('pending', 'retry_scheduled') AND scheduled_at <= ?
                ORDER BY scheduled_at, created_at
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            job_ids = [row["job_id"] for row in rows]
            for job_id in job_ids:
                conn.execute(
                    """
                    UPDATE sync_jobs
                    SET status = 'processing', updated_at = ?, started_at = ?
                    WHERE job_id = ?
                    """,
                    (now, now, job_id),
                )
        for job_id in job_ids:
            self.add_event(job_id, "started")
        return [self.get(job_id) for job_id in job_ids]

    def mark_succeeded(self, job_id: str) -> None:
        now = now_iso()
        self._update(job_id, status="succeeded", finished_at=now, last_error=None)
        self.add_event(job_id, "succeeded")

    def schedule_retry(self, job_id: str, retry_count: int, scheduled_at: str, error: str) -> None:
        self._update(
            job_id,
            status="retry_scheduled",
            retry_count=retry_count,
            scheduled_at=scheduled_at,
            last_error=error,
        )
        self.add_event(job_id, "retry_scheduled", error)

    def mark_failed(self, job_id: str, retry_count: int, error: str) -> None:
        self._update(
            job_id,
            status="failed",
            retry_count=retry_count,
            finished_at=now_iso(),
            last_error=error,
        )
        self.add_event(job_id, "failed", error)

    def retry(self, job_id: str) -> dict[str, Any] | None:
        job = self.get(job_id)
        if not job:
            return None
        self._update(
            job_id,
            status="pending",
            scheduled_at=now_iso(),
            last_error=None,
            finished_at=None,
        )
        self.add_event(job_id, "retry_requested")
        return self.get(job_id)

    def status_summary(self, collection: str) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM sync_jobs WHERE collection = ? GROUP BY status",
                (collection,),
            ).fetchall()
            last_success = conn.execute(
                """
                SELECT finished_at FROM sync_jobs
                WHERE collection = ? AND status = 'succeeded'
                ORDER BY finished_at DESC LIMIT 1
                """,
                (collection,),
            ).fetchone()
        counts = {row["status"]: row["count"] for row in rows}
        return {
            "collection": collection,
            "pending": counts.get("pending", 0),
            "processing": counts.get("processing", 0),
            "retry_scheduled": counts.get("retry_scheduled", 0),
            "succeeded": counts.get("succeeded", 0),
            "failed": counts.get("failed", 0),
            "last_success_at": last_success["finished_at"] if last_success else None,
        }

    def add_event(
        self,
        job_id: str,
        event_type: str,
        message: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        import uuid

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_job_events (event_id, job_id, event_type, message, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"event_{uuid.uuid4().hex}",
                    job_id,
                    event_type,
                    message,
                    json.dumps(data or {}, ensure_ascii=False, sort_keys=True),
                    now_iso(),
                ),
            )

    def _update(self, job_id: str, **fields: Any) -> None:
        fields["updated_at"] = now_iso()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE sync_jobs SET {assignments} WHERE job_id = ?",
                [*fields.values(), job_id],
            )

    def _decode(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item
