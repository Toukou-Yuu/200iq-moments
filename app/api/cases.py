from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError

from app.models import CaseCreate, CaseStatus, CaseUpdate
from app.repositories.case_repository import CaseRepository, case_summary
from app.services.markdown_renderer import render_case_markdown
from app.services.slug import slugify
from app.services.sync_service import SyncService

from .deps import get_case_repository, get_sync_service

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/validate")
def validate_case(payload: dict) -> dict[str, object]:
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


@router.post("/preview")
def preview_case(payload: dict) -> dict[str, object]:
    validation = validate_case(payload)
    if not validation["valid"]:
        return {"valid": False, "markdown": "", "warnings": validation["errors"]}
    case = CaseCreate.model_validate(payload)
    record = case_to_preview_record(case)
    return {
        "valid": True,
        "markdown": render_case_markdown(record),
        "warnings": validation["warnings"],
    }


@router.get("")
def list_cases(
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    status: CaseStatus | None = None,
    loss_type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "date_desc",
) -> dict[str, object]:
    cases = repo.list_cases(status, loss_type, tag, q, date_from, date_to, sort)
    items = cases[offset : offset + limit]
    return {
        "items": [case_summary(case) for case in items],
        "total": len(cases),
        "limit": limit,
        "offset": offset,
    }


@router.post("")
def create_case(
    case: CaseCreate,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    record = repo.create_case(case)
    index_sync = sync.enqueue_case(record, "upsert")
    return {
        "created": True,
        "case_id": record.id,
        "slug": record.slug,
        "path": str(repo.case_path(record)),
        "index_sync": index_sync,
    }


@router.get("/{case_id}")
def get_case(
    case_id: str,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
) -> dict[str, object]:
    return repo.get_case(case_id).model_dump(mode="json")


@router.patch("/{case_id}")
def update_case(
    case_id: str,
    patch: CaseUpdate,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    previous = repo.get_case(case_id)
    record, updated_fields = repo.update_case(case_id, patch)
    index_sync = (
        {"enabled": True, "skipped": True, "reason": "content_not_changed"}
        if not updated_fields
        else sync.enqueue_case(record, sync_action(previous.status, record.status))
    )
    return {
        "updated": True,
        "case_id": record.id,
        "updated_fields": updated_fields,
        "index_sync": index_sync,
    }


@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
    mode: str = "archive",
) -> dict[str, object]:
    status = CaseStatus.DELETED if mode == "delete" else CaseStatus.ARCHIVED
    record = repo.archive_case(case_id, status)
    action = "delete" if status == CaseStatus.DELETED else "archive"
    return {
        "case_id": record.id,
        "status": record.status.value,
        "index_sync": sync.enqueue_case(record, action),
    }


@router.get("/{case_id}/markdown")
def get_case_markdown(
    case_id: str,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "format": "markdown",
        "content": repo.render_markdown(case_id),
    }


def case_to_preview_record(case: CaseCreate):
    from datetime import datetime

    from app.models import CaseRecord

    now = datetime.now().astimezone()
    return CaseRecord(
        **case.model_dump(),
        id="XXX",
        slug=slugify(case.title),
        created_at=now,
        updated_at=now,
    )


def sync_action(previous: CaseStatus, current: CaseStatus) -> str:
    if current == CaseStatus.DELETED:
        return "delete"
    if current == CaseStatus.ARCHIVED:
        return "archive"
    if current == CaseStatus.PUBLISHED and previous in {CaseStatus.ARCHIVED, CaseStatus.DELETED}:
        return "restore"
    return "upsert"
