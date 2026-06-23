from datetime import date, datetime, timezone

import httpx

from app.config import Settings
from app.models import CaseRecord, CaseStatus
from app.repositories.sync_job_repository import SyncJobRepository
from app.services.retrieval_client import RetrievalClient
from app.services.sync_service import SyncService


def make_case() -> CaseRecord:
    timestamp = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    return CaseRecord(
        id="001",
        slug="airport-subscription",
        title="机场套餐误判",
        date=date(2025, 6, 20),
        status=CaseStatus.PUBLISHED,
        summary="看到价格划算就下单。",
        reality="套餐一个月过期。",
        avoidance=["确认有效期"],
        checklist=["有效期是多久？"],
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_service(tmp_path, max_retries=5):
    settings = Settings(data_dir=tmp_path, sync_worker_max_retries=max_retries)
    repository = SyncJobRepository(settings.sync_db_path)
    return SyncService(repository, settings), repository


def test_enqueue_case_is_idempotent(tmp_path):
    service, repository = make_service(tmp_path)

    first = service.enqueue_case(make_case(), "upsert")
    repeated = service.enqueue_case(make_case(), "upsert")

    assert first["skipped"] is False
    assert repeated["skipped"] is True
    assert len(repository.list_jobs()) == 1


def test_worker_dispatches_upsert_and_marks_succeeded(tmp_path):
    service, repository = make_service(tmp_path)
    service.enqueue_case(make_case(), "upsert")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    client = RetrievalClient(
        "http://retrieval-api:8000",
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert service.process_due_jobs(client) == 1
    job = repository.list_jobs()[0]
    assert job["status"] == "succeeded"
    assert [request.url.path for request in requests] == [
        "/v1/collections",
        "/v1/documents/upsert",
    ]


def test_worker_retries_server_error_and_fails_client_error(tmp_path):
    service, repository = make_service(tmp_path)
    service.enqueue_case(make_case(), "upsert")

    def server_error(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    retry_client = RetrievalClient(
        "http://retrieval-api:8000",
        httpx.Client(transport=httpx.MockTransport(server_error)),
    )
    service.process_due_jobs(retry_client)
    assert repository.list_jobs()[0]["status"] == "retry_scheduled"

    second_service, second_repository = make_service(tmp_path / "client-error")
    second_service.enqueue_case(make_case(), "upsert")

    def client_error(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/collections":
            return httpx.Response(200, json={})
        return httpx.Response(400, json={})

    failed_client = RetrievalClient(
        "http://retrieval-api:8000",
        httpx.Client(transport=httpx.MockTransport(client_error)),
    )
    second_service.process_due_jobs(failed_client)
    assert second_repository.list_jobs()[0]["status"] == "failed"
