import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_case_repository
from app.main import app
from app.repositories.case_repository import CaseRepository


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_case_repository] = lambda: CaseRepository(tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_index_rebuild_and_sync(client):
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
    sync = client.post("/v1/index/sync", json={"since": "2025-01-01T00:00:00+08:00"})

    assert rebuild.status_code == 200
    assert rebuild.json()["items"][0]["case_id"] == "001"
    assert "套餐一个月过期" in rebuild.json()["items"][0]["text"]
    assert sync.status_code == 200
    assert sync.json()["events"][0]["case_id"] == "001"
