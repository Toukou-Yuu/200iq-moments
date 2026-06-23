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


def test_stats_summary_and_timeline(client):
    client.post(
        "/v1/cases",
        json={
            "title": "机场套餐误判",
            "date": "2025-06-20",
            "loss": {"amount": 19.9, "currency": "CNY", "types": ["money"]},
            "summary": "看到单位价格划算就下单。",
            "reality": "套餐一个月过期。",
            "avoidance": ["确认有效期"],
            "checklist": ["有效期是多久？"],
            "tags": ["subscription"],
        },
    )

    summary = client.get("/v1/stats/summary")
    timeline = client.get("/v1/stats/timeline")

    assert summary.status_code == 200
    assert summary.json()["total_cases"] == 1
    assert summary.json()["total_loss"] == {"CNY": 19.9}
    assert summary.json()["loss_type_count"]["money"] == 1
    assert summary.json()["top_tags"] == [{"tag": "subscription", "count": 1}]
    assert timeline.status_code == 200
    assert timeline.json()["items"][0]["month"] == "2025-06"
