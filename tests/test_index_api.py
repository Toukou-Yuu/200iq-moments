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
    app.dependency_overrides[get_case_repository] = lambda: CaseRepository(tmp_path)
    settings = Settings(data_dir=tmp_path)
    app.dependency_overrides[get_sync_service] = lambda: SyncService(
        SyncJobRepository(settings.sync_db_path),
        settings,
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_index_rebuild_sync_and_export(client):
    client.post(
        "/v1/cases",
        json={
            "title": "机场套餐误判",
            "date": "2025-06-20",
            "summary": "看到单位价格划算就下单。",
            "reality": "套餐一个月过期。",
            "avoidance": ["确认有效期"],
            "checklist": ["有效期是多久？"],
        },
    )

    rebuild = client.post("/v1/index/rebuild")
    sync = client.post("/v1/index/sync/001")
    exported = client.get("/v1/export/documents")
    status = client.get("/v1/index/status")

    assert rebuild.status_code == 200
    assert sync.status_code == 200
    assert sync.json()["case_id"] == "001"
    assert exported.json()["documents"][0]["id"] == "200iq:case:001"
    assert "套餐一个月过期" in exported.json()["documents"][0]["text"]
    assert status.json()["pending"] >= 1
