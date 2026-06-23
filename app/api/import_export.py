from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import CaseStatus
from app.repositories.case_repository import CaseRepository
from app.services.retrieval_document_mapper import RETRIEVAL_COLLECTION, map_case_to_document
from app.services.sync_service import SyncService

from .deps import get_case_repository, get_sync_service

router = APIRouter(tags=["import-export"])


@router.post("/import/markdown")
def import_markdown(
    payload: dict,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
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
        "index_sync": sync.enqueue_case(
            record,
            "delete" if record.status == CaseStatus.DELETED else "upsert",
        ),
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


@router.get("/export/documents")
def export_documents(
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    status: str = "all",
) -> dict[str, object]:
    if status == "all":
        cases = repo.list_all_cases()
    else:
        try:
            cases = repo.list_cases(status=CaseStatus(status))
        except ValueError:
            return {"error": "status must be draft, published, archived, deleted, or all"}
    return {
        "collection": RETRIEVAL_COLLECTION,
        "documents": [map_case_to_document(case) for case in cases],
    }
