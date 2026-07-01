from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp

from app.mcp.tools import TOOL_SPECS, call_case_tool


def create_mcp_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8201,
    path: str = "/mcp",
) -> FastMCP:
    server = FastMCP(
        "200iq-moments",
        instructions=(
            "Agent-facing tools for hikari's 200iq-moments case memory. Use these "
            "tools to validate, preview, create, search, update, archive, and sync "
            "structured mistake/lesson cases."
        ),
        host=host,
        port=port,
        streamable_http_path=path,
        stateless_http=True,
        json_response=True,
    )
    _register_tools(server)
    return server


def create_mcp_http_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8201,
    path: str = "/mcp",
) -> ASGIApp:
    return create_mcp_server(host=host, port=port, path=path).streamable_http_app()


def run_stdio_server() -> None:
    create_mcp_server().run("stdio")


def run_streamable_http_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8201,
    path: str = "/mcp",
) -> None:
    create_mcp_server(host=host, port=port, path=path).run("streamable-http")


def _register_tools(server: FastMCP) -> None:
    for tool_name, tool in [
        ("case_get_template", case_get_template_tool),
        ("case_validate", case_validate_tool),
        ("case_preview", case_preview_tool),
        ("case_create", case_create_tool),
        ("case_update", case_update_tool),
        ("case_search", case_search_tool),
        ("case_get", case_get_tool),
        ("case_archive", case_archive_tool),
        ("case_sync_index", case_sync_index_tool),
        ("case_rebuild_index", case_rebuild_index_tool),
        ("case_stats", case_stats_tool),
    ]:
        server.tool(name=tool_name, description=TOOL_SPECS[tool_name].description)(tool)


def case_get_template_tool(format: str = "json") -> dict[str, Any]:
    return call_case_tool("case_get_template", {"format": format})


def case_validate_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return call_case_tool("case_validate", {"payload": payload})


def case_preview_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return call_case_tool("case_preview", {"payload": payload})


def case_create_tool(payload: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    return call_case_tool("case_create", {"payload": payload, "dry_run": dry_run})


def case_update_tool(
    case_id: str,
    patch: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    return call_case_tool(
        "case_update",
        {"case_id": case_id, "patch": patch, "dry_run": dry_run},
    )


def case_search_tool(
    status: str | None = None,
    loss_type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "date_desc",
) -> dict[str, Any]:
    return call_case_tool(
        "case_search",
        {
            "status": status,
            "loss_type": loss_type,
            "tag": tag,
            "q": q,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
            "offset": offset,
            "sort": sort,
        },
    )


def case_get_tool(case_id: str, include_markdown: bool = False) -> dict[str, Any]:
    return call_case_tool(
        "case_get",
        {"case_id": case_id, "include_markdown": include_markdown},
    )


def case_archive_tool(
    case_id: str,
    mode: str = "archive",
    dry_run: bool = False,
) -> dict[str, Any]:
    return call_case_tool(
        "case_archive",
        {"case_id": case_id, "mode": mode, "dry_run": dry_run},
    )


def case_sync_index_tool(case_id: str, dry_run: bool = False) -> dict[str, Any]:
    return call_case_tool("case_sync_index", {"case_id": case_id, "dry_run": dry_run})


def case_rebuild_index_tool(dry_run: bool = True) -> dict[str, Any]:
    return call_case_tool("case_rebuild_index", {"dry_run": dry_run})


def case_stats_tool(kind: str = "summary") -> dict[str, Any]:
    return call_case_tool("case_stats", {"kind": kind})
