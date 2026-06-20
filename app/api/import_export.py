from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import CaseStatus
from app.repositories.case_repository import CaseRepository

from .deps import get_case_repository

router = APIRouter(tags=["import-export"])


@router.post("/import/markdown")
def import_markdown(
    payload: dict,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
) -> dict[str, object]:
    record, created, updated, warnings = repo.import_markdown(
        payload.get("content", ""),
        payload.get("mode", "upsert"),
    )
    return {
        "imported": True,
        "created": created,
        "updated": updated,
        "case_id": record.id,
        "warnings": warnings,
    }


@router.get("/export/json")
def export_json(
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    status: CaseStatus | None = None,
) -> dict[str, object]:
    from datetime import datetime

    cases = repo.list_cases(status=status)
    return {
        "items": [case.model_dump(mode="json") for case in cases],
        "total": len(cases),
        "exported_at": datetime.now().astimezone().isoformat(),
    }


@router.get("/export/markdown")
def export_markdown(
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    status: CaseStatus | None = None,
) -> dict[str, object]:
    cases = repo.list_cases(status=status)
    return {
        "items": [
            {
                "case_id": case.id,
                "path": str(repo.case_path(case)),
                "content": repo.render_markdown(case.id),
            }
            for case in cases
        ]
    }
