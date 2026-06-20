from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_case_template_returns_required_fields():
    response = client.get("/v1/templates/case")

    assert response.status_code == 200
    body = response.json()
    assert body["required_fields"] == [
        "title",
        "date",
        "summary",
        "reality",
        "avoidance",
        "checklist",
    ]


def test_case_markdown_template_returns_content():
    response = client.get("/v1/templates/case/markdown")

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "markdown"
    assert "Case Study" in body["content"]
