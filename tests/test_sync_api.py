import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_case_repository, get_sync_service
from app.config import Settings
from app.main import app
from app.repositories.case_repository import CaseRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.services.sync_service import SyncService


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path)
    sync = SyncService(SyncJobRepository(settings.sync_db_path), settings)
    app.dependency_overrides[get_case_repository] = lambda: CaseRepository(tmp_path)
    app.dependency_overrides[get_sync_service] = lambda: sync
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_case(client):
    return client.post(
        "/v1/cases",
        json={
            "title": "机场套餐误判",
            "date": "2025-06-20",
            "summary": "看到单位价格划算就下单。",
            "reality": "套餐一个月过期。",
            "avoidance": ["确认有效期"],
            "checklist": ["有效期是多久？"],
            "tags": ["subscription"],
        },
    )


def test_case_mutations_create_expected_sync_jobs(client):
    created = create_case(client)
    unchanged = client.patch("/v1/cases/001", json={"tags": ["subscription"]})
    archived = client.delete("/v1/cases/001")
    restored = client.patch("/v1/cases/001", json={"status": "published"})
    deleted = client.delete("/v1/cases/001", params={"mode": "delete"})
    jobs = client.get("/v1/index/jobs").json()["items"]

    assert created.json()["index_sync"]["status"] == "pending"
    assert unchanged.json()["index_sync"]["skipped"] is True
    assert archived.json()["index_sync"]["status"] == "pending"
    assert restored.json()["index_sync"]["status"] == "pending"
    assert deleted.json()["index_sync"]["status"] == "pending"
    assert {job["action"] for job in jobs} == {"upsert", "archive", "restore", "delete"}


def test_archive_after_restore_creates_new_archive_job(client):
    create_case(client)
    first_archive = client.delete("/v1/cases/001").json()["index_sync"]["job_id"]
    client.patch("/v1/cases/001", json={"status": "published"})
    second_archive = client.delete("/v1/cases/001").json()["index_sync"]

    assert second_archive["skipped"] is False
    assert second_archive["job_id"] != first_archive


def test_export_documents_and_rebuild_job(client):
    create_case(client)

    exported = client.get("/v1/export/documents")
    rebuild = client.post("/v1/index/rebuild")
    job = client.get(f"/v1/index/jobs/{rebuild.json()['job_id']}")

    assert exported.json()["collection"] == "200iq_cases"
    assert exported.json()["documents"][0]["id"] == "200iq:case:001"
    assert rebuild.json()["status"] == "pending"
    assert job.json()["action"] == "rebuild"
