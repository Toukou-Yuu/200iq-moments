import asyncio

from app.mcp.server import create_mcp_server
from app.mcp.tools import TOOL_SPECS, call_case_tool

EXPECTED_TOOLS = {
    "case_get_template",
    "case_validate",
    "case_preview",
    "case_create",
    "case_update",
    "case_search",
    "case_get",
    "case_archive",
    "case_sync_index",
    "case_rebuild_index",
    "case_stats",
}


def test_mcp_tool_inventory_matches_architecture_standard() -> None:
    server = create_mcp_server()

    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert tool_names == EXPECTED_TOOLS
    for tool in tools:
        assert tool.description
        assert tool.name in TOOL_SPECS
        assert TOOL_SPECS[tool.name].permission in {"read", "write", "admin"}


def test_tool_calls_return_standard_success_envelope(tmp_path, monkeypatch) -> None:
    from app.api import deps
    from app.config import Settings
    from app.repositories.case_repository import CaseRepository
    from app.repositories.sync_job_repository import SyncJobRepository
    from app.services.sync_service import SyncService

    settings = Settings(data_dir=tmp_path)
    monkeypatch.setattr(deps, "get_case_repository", lambda: CaseRepository(tmp_path))
    monkeypatch.setattr(
        deps,
        "get_sync_service",
        lambda: SyncService(SyncJobRepository(settings.sync_db_path), settings),
    )

    result = call_case_tool("case_get_template", {"format": "json"})

    assert result["ok"] is True
    assert result["summary"] == "Read 200iq case JSON template."
    assert result["data"]["template"]["format"] == "case-json"
    assert result["warnings"] == []


def test_tool_calls_return_standard_error_envelope(tmp_path, monkeypatch) -> None:
    from app.api import deps
    from app.repositories.case_repository import CaseRepository

    monkeypatch.setattr(deps, "get_case_repository", lambda: CaseRepository(tmp_path))

    result = call_case_tool("case_get", {"case_id": "999"})

    assert result["ok"] is False
    assert result["error"] == {
        "code": "CASE_NOT_FOUND",
        "message": "Case not found: 999",
        "retryable": False,
        "suggested_action": "Call case_search first, then retry with an existing case_id.",
    }
