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


def test_import_legacy_markdown(client):
    content = """## Case Study #001 — 机场套餐误判

**日期**：2025-06-20

### 事情经过

看到单位价格划算就下单。

### 现实情况

套餐一个月过期。

### 本可以避免，如果我……

- [ ] 确认有效期

### 下次检查清单

- [ ] 有效期是多久？
"""

    response = client.post("/v1/import/markdown", json={"content": content, "mode": "upsert"})

    assert response.status_code == 200
    assert response.json()["imported"] is True
    assert response.json()["case_id"] == "001"


def test_export_json_and_markdown(client):
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

    json_response = client.get("/v1/export/json")
    markdown_response = client.get("/v1/export/markdown")

    assert json_response.status_code == 200
    assert json_response.json()["total"] == 1
    assert markdown_response.status_code == 200
    assert markdown_response.json()["items"][0]["case_id"] == "001"
