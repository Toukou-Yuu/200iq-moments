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


def sample_case() -> dict:
    return {
        "title": "机场套餐误判",
        "date": "2025-06-20",
        "loss": {
            "amount": 19.9,
            "currency": "CNY",
            "types": ["money", "dignity"],
            "description": "金钱 + 尊严",
        },
        "summary": "看到单位价格划算就下单。",
        "genius_logic": "买！",
        "reality": "套餐一个月过期。",
        "gap_analysis": [
            {"dimension": "有效期", "assumed": "不限时", "actual": "一个月"}
        ],
        "avoidance": ["确认有效期"],
        "checklist": ["有效期是多久？"],
        "mood": "麻了",
        "tags": ["subscription"],
    }


def test_validate_case_success(client):
    response = client.post("/v1/cases/validate", json=sample_case())

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_case_missing_required_field_fails(client):
    payload = sample_case()
    payload.pop("summary")

    response = client.post("/v1/cases/validate", json=payload)

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_preview_case_returns_markdown(client):
    response = client.post("/v1/cases/preview", json=sample_case())

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert "Case Study #XXX" in response.json()["markdown"]


def test_case_crud_flow(client):
    created = client.post("/v1/cases", json=sample_case())
    assert created.status_code == 200
    assert created.json()["case_id"] == "001"

    got = client.get("/v1/cases/001")
    assert got.status_code == 200
    assert got.json()["title"] == "机场套餐误判"

    listed = client.get("/v1/cases", params={"tag": "subscription", "status": "published"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    patched = client.patch("/v1/cases/001", json={"tags": ["subscription", "traffic"]})
    assert patched.status_code == 200
    assert patched.json()["updated_fields"] == ["tags"]

    markdown = client.get("/v1/cases/001/markdown")
    assert markdown.status_code == 200
    assert markdown.json()["format"] == "markdown"

    deleted = client.delete("/v1/cases/001")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "archived"
