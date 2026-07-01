from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

from pydantic import ValidationError

from app.api import deps
from app.api.templates import CASE_MARKDOWN_TEMPLATE, LOSS_TYPES, OPTIONAL_FIELDS, REQUIRED_FIELDS, STATUSES
from app.models import CaseCreate, CaseRecord, CaseStatus, CaseUpdate
from app.repositories.case_repository import (
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidMarkdownError,
    case_summary,
)
from app.services.markdown_renderer import render_case_markdown
from app.services.retrieval_document_mapper import document_id_for_case
from app.services.slug import slugify
from app.services.stats_service import summary as stats_summary
from app.services.stats_service import timeline as stats_timeline

Permission = Literal["read", "write", "admin"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    permission: Permission
    description: str


ToolResult = dict[str, Any]
RawTool = Callable[..., Any]


def success(
    summary: str,
    data: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ToolResult:
    return {
        "ok": True,
        "summary": summary,
        "data": data or {},
        "warnings": warnings or [],
    }


def error(
    *,
    code: str,
    message: str,
    retryable: bool = False,
    suggested_action: str,
) -> ToolResult:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "suggested_action": suggested_action,
        },
    }


def case_get_template(format: str = "json") -> ToolResult:
    if format == "markdown":
        return success(
            "Read 200iq case Markdown template.",
            {"template": {"version": "1.0", "format": "markdown", "content": CASE_MARKDOWN_TEMPLATE}},
        )
    if format != "json":
        return error(
            code="INVALID_TEMPLATE_FORMAT",
            message="format must be json or markdown",
            suggested_action="Retry with format='json' or format='markdown'.",
        )
    template = {
        "version": "1.0",
        "format": "case-json",
        "required_fields": REQUIRED_FIELDS,
        "optional_fields": OPTIONAL_FIELDS,
        "enums": {"loss.types": LOSS_TYPES, "status": STATUSES},
        "schema": {
            "title": "string",
            "date": "YYYY-MM-DD",
            "loss": {
                "amount": "number|null",
                "currency": "string|null",
                "types": ["string"],
                "description": "string|null",
            },
            "summary": "string",
            "genius_logic": "string|null",
            "reality": "string",
            "gap_analysis": [{"dimension": "string", "assumed": "string", "actual": "string"}],
            "avoidance": ["string"],
            "checklist": ["string"],
            "mood": "string|null",
            "tags": ["string"],
        },
    }
    return success("Read 200iq case JSON template.", {"template": template})


def case_validate(payload: dict[str, Any]) -> ToolResult:
    validation = _validate_case_payload(payload)
    summary = "Case payload is valid." if validation["valid"] else "Case payload is invalid."
    return success(summary, validation, cast(list[str], validation.get("warnings", [])))


def case_preview(payload: dict[str, Any]) -> ToolResult:
    validation = _validate_case_payload(payload)
    if not validation["valid"]:
        return success(
            "Case payload is invalid; preview was not generated.",
            {"valid": False, "markdown": "", "validation": validation},
            cast(list[str], validation.get("errors", [])),
        )
    case = CaseCreate.model_validate(payload)
    record = _case_to_preview_record(case)
    return success(
        f"Generated preview for case: {case.title}",
        {
            "valid": True,
            "case": record.model_dump(mode="json"),
            "markdown": render_case_markdown(record),
        },
        cast(list[str], validation.get("warnings", [])),
    )


def case_create(payload: dict[str, Any], dry_run: bool = False) -> ToolResult:
    case = CaseCreate.model_validate(payload)
    if dry_run:
        record = _case_to_preview_record(case)
        return success(
            f"Validated create request for case: {case.title}",
            {
                "case": record.model_dump(mode="json"),
                "markdown": render_case_markdown(record),
                "dry_run": True,
            },
        )
    repo = deps.get_case_repository()
    sync = deps.get_sync_service()
    record = repo.create_case(case)
    index_sync = sync.enqueue_case(record, "upsert")
    return success(
        f"Created 200iq case {record.id}: {record.title}",
        {
            "case_id": record.id,
            "slug": record.slug,
            "path": str(repo.case_path(record)),
            "index_sync": index_sync,
        },
    )


def case_update(case_id: str, patch: dict[str, Any], dry_run: bool = False) -> ToolResult:
    update = CaseUpdate.model_validate(patch)
    repo = deps.get_case_repository()
    previous = repo.get_case(case_id)
    update_data = update.model_dump(exclude_unset=True)
    previous_data = previous.model_dump()
    updated_fields = [
        field for field, value in update_data.items() if previous_data[field] != value
    ]
    if dry_run:
        return success(
            f"Validated update request for 200iq case {case_id}.",
            {"case_id": case_id, "updated_fields": updated_fields, "dry_run": True},
        )
    record, updated_fields = repo.update_case(case_id, update)
    index_sync = (
        {"enabled": True, "skipped": True, "reason": "content_not_changed"}
        if not updated_fields
        else deps.get_sync_service().enqueue_case(record, _sync_action(previous.status, record.status))
    )
    return success(
        f"Updated 200iq case {record.id}: {', '.join(updated_fields) or 'no fields changed'}.",
        {"case_id": record.id, "updated_fields": updated_fields, "index_sync": index_sync},
    )


def case_search(
    status: str | None = None,
    loss_type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "date_desc",
) -> ToolResult:
    limit = _clamp_limit(limit, maximum=100)
    offset = max(offset, 0)
    parsed_status = CaseStatus(status) if status else None
    cases = deps.get_case_repository().list_cases(
        parsed_status,
        loss_type,
        tag,
        q,
        date_from,
        date_to,
        sort,
    )
    items = [_agent_case_summary(case) for case in cases[offset : offset + limit]]
    return success(
        f"Found {len(items)} 200iq cases.",
        {
            "cases": items,
            "count": len(items),
            "total": len(cases),
            "limit": limit,
            "offset": offset,
        },
    )


def case_get(case_id: str, include_markdown: bool = False) -> ToolResult:
    repo = deps.get_case_repository()
    record = repo.get_case(case_id)
    data: dict[str, Any] = {"case": record.model_dump(mode="json")}
    if include_markdown:
        data["markdown"] = repo.render_markdown(case_id)
    return success(f"Read 200iq case {case_id}: {record.title}", data)


def case_archive(case_id: str, mode: str = "archive", dry_run: bool = False) -> ToolResult:
    if mode not in {"archive", "delete"}:
        return error(
            code="INVALID_ARCHIVE_MODE",
            message="mode must be archive or delete",
            suggested_action="Retry with mode='archive' or mode='delete'.",
        )
    repo = deps.get_case_repository()
    current = repo.get_case(case_id)
    status = CaseStatus.DELETED if mode == "delete" else CaseStatus.ARCHIVED
    if dry_run:
        return success(
            f"Validated {mode} request for 200iq case {case_id}.",
            {"case_id": case_id, "current_status": current.status.value, "new_status": status.value, "dry_run": True},
        )
    record = repo.archive_case(case_id, status)
    action = "delete" if status == CaseStatus.DELETED else "archive"
    index_sync = deps.get_sync_service().enqueue_case(record, action)
    return success(
        f"{action.title()}d 200iq case {record.id}.",
        {"case_id": record.id, "status": record.status.value, "index_sync": index_sync},
    )


def case_sync_index(case_id: str, dry_run: bool = False) -> ToolResult:
    case = deps.get_case_repository().get_case(case_id)
    action = "delete" if case.status == CaseStatus.DELETED else "upsert"
    document_id = document_id_for_case(case.id)
    if dry_run:
        return success(
            f"Validated retrieval-index sync for 200iq case {case.id}.",
            {"case_id": case.id, "document_id": document_id, "action": action, "dry_run": True},
        )
    result = deps.get_sync_service().enqueue_case(case, action)
    return success(
        f"Queued retrieval-index sync for 200iq case {case.id}.",
        {"case_id": case.id, "document_id": document_id, "action": action, "index_sync": result},
    )


def case_rebuild_index(dry_run: bool = True) -> ToolResult:
    cases = deps.get_case_repository().list_cases()
    if dry_run:
        return success(
            f"Validated retrieval-index rebuild for {len(cases)} 200iq cases.",
            {"case_count": len(cases), "dry_run": True},
        )
    result = deps.get_sync_service().enqueue_rebuild(cases)
    return success(
        f"Queued retrieval-index rebuild for {len(cases)} 200iq cases.",
        {"case_count": len(cases), "index_sync": result},
    )


def case_stats(kind: str = "summary") -> ToolResult:
    cases = deps.get_case_repository().list_cases()
    if kind == "summary":
        data = {"summary": stats_summary(cases)}
    elif kind == "timeline":
        data = {"timeline": stats_timeline(cases)}
    elif kind == "all":
        data = {"summary": stats_summary(cases), "timeline": stats_timeline(cases)}
    else:
        return error(
            code="INVALID_STATS_KIND",
            message="kind must be summary, timeline, or all",
            suggested_action="Retry with kind='summary', 'timeline', or 'all'.",
        )
    return success(f"Read 200iq case {kind} stats.", data)


TOOL_SPECS: dict[str, ToolSpec] = {
    "case_get_template": ToolSpec(
        "case_get_template",
        "read",
        "Read the JSON or Markdown template for a 200iq case. Read-only.",
    ),
    "case_validate": ToolSpec(
        "case_validate",
        "read",
        "Validate a proposed case payload and return normalized fields. Read-only.",
    ),
    "case_preview": ToolSpec(
        "case_preview",
        "read",
        "Render a proposed case as Markdown without saving it. Read-only.",
    ),
    "case_create": ToolSpec(
        "case_create",
        "write",
        "Create a 200iq case and enqueue retrieval indexing unless dry_run=true.",
    ),
    "case_update": ToolSpec(
        "case_update",
        "write",
        "Update a 200iq case and enqueue retrieval-index sync unless dry_run=true.",
    ),
    "case_search": ToolSpec(
        "case_search",
        "read",
        "Search/list 200iq cases by status, tag, loss type, text, and date. Read-only.",
    ),
    "case_get": ToolSpec(
        "case_get",
        "read",
        "Read a 200iq case by case_id, optionally including rendered Markdown. Read-only.",
    ),
    "case_archive": ToolSpec(
        "case_archive",
        "write",
        "Archive or soft-delete a 200iq case and enqueue retrieval sync unless dry_run=true.",
    ),
    "case_sync_index": ToolSpec(
        "case_sync_index",
        "write",
        "Queue retrieval-index sync for one 200iq case unless dry_run=true.",
    ),
    "case_rebuild_index": ToolSpec(
        "case_rebuild_index",
        "admin",
        "Queue a full retrieval-index rebuild for 200iq cases. Dry-run by default.",
    ),
    "case_stats": ToolSpec(
        "case_stats",
        "read",
        "Read 200iq case summary and timeline statistics. Read-only.",
    ),
}

TOOLS: dict[str, RawTool] = {
    "case_get_template": case_get_template,
    "case_validate": case_validate,
    "case_preview": case_preview,
    "case_create": case_create,
    "case_update": case_update,
    "case_search": case_search,
    "case_get": case_get,
    "case_archive": case_archive,
    "case_sync_index": case_sync_index,
    "case_rebuild_index": case_rebuild_index,
    "case_stats": case_stats,
}


def call_case_tool(tool_name: str, arguments: dict[str, Any]) -> ToolResult:
    if tool_name not in TOOLS:
        return error(
            code="TOOL_NOT_FOUND",
            message=f"Unknown 200iq MCP tool: {tool_name}",
            suggested_action="Call MCP list_tools and retry with a supported case_* tool name.",
        )
    try:
        result = TOOLS[tool_name](**arguments)
    except CaseNotFoundError as exc:
        return error(
            code="CASE_NOT_FOUND",
            message=f"Case not found: {exc}",
            suggested_action="Call case_search first, then retry with an existing case_id.",
        )
    except CaseAlreadyExistsError as exc:
        return error(
            code="CASE_ALREADY_EXISTS",
            message=f"Case already exists: {exc}",
            suggested_action="Use case_update for existing cases or choose create mode carefully.",
        )
    except InvalidMarkdownError as exc:
        return error(
            code="INVALID_MARKDOWN",
            message="Invalid markdown",
            suggested_action=f"Fix markdown warnings and retry: {', '.join(exc.warnings)}",
        )
    except ValidationError as exc:
        return error(
            code="CASE_VALIDATION_ERROR",
            message=str(exc),
            suggested_action="Call case_get_template, fix the case payload, then retry.",
        )
    except ValueError as exc:
        return error(
            code="INVALID_REQUEST",
            message=str(exc),
            suggested_action="Fix the tool arguments to match the documented schema, then retry.",
        )
    except Exception as exc:
        return error(
            code="TOOL_CALL_FAILED",
            message=str(exc),
            retryable=True,
            suggested_action="Inspect 200iq-moments settings and logs, then retry.",
        )
    if isinstance(result, dict) and "ok" in result:
        return cast(ToolResult, result)
    return success(f"{tool_name} completed.", {"result": result})


def _validate_case_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        case = CaseCreate.model_validate(payload)
    except ValidationError as exc:
        return {
            "valid": False,
            "errors": [error["msg"] for error in exc.errors()],
            "warnings": [],
            "normalized": {},
        }
    warnings = []
    if case.loss and case.loss.amount is None:
        warnings.append("loss.amount is null")
    if not case.tags:
        warnings.append("tags is empty")
    return {
        "valid": True,
        "errors": [],
        "warnings": warnings,
        "normalized": {
            "title": case.title,
            "date": case.date.isoformat(),
            "slug": slugify(case.title),
        },
    }


def _case_to_preview_record(case: CaseCreate) -> CaseRecord:
    from datetime import datetime

    now = datetime.now().astimezone()
    return CaseRecord(
        **case.model_dump(),
        id="XXX",
        slug=slugify(case.title),
        created_at=now,
        updated_at=now,
    )


def _agent_case_summary(case: CaseRecord) -> dict[str, Any]:
    item = case_summary(case)
    item.update(
        {
            "summary_preview": _preview(case.summary, 300),
            "reality_preview": _preview(case.reality, 300),
            "document_id": document_id_for_case(case.id),
        }
    )
    return item


def _preview(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _sync_action(previous: CaseStatus, current: CaseStatus) -> str:
    if current == CaseStatus.DELETED:
        return "delete"
    if current == CaseStatus.ARCHIVED:
        return "archive"
    if current == CaseStatus.PUBLISHED and previous in {CaseStatus.ARCHIVED, CaseStatus.DELETED}:
        return "restore"
    return "upsert"


def _clamp_limit(value: int, *, maximum: int) -> int:
    return max(1, min(int(value), maximum))
