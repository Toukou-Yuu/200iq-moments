from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.case_repository import CaseRepository
from app.services.retrieval_document_mapper import RETRIEVAL_COLLECTION, document_id_for_case
from app.services.sync_service import SyncService

from .deps import get_case_repository, get_sync_service

router = APIRouter(prefix="/index", tags=["index"])


@router.post("/sync/{case_id}")
def sync_case(
    case_id: str,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    case = repo.get_case(case_id)
    action = "delete" if case.status.value == "deleted" else "upsert"
    result = sync.enqueue_case(case, action)
    return {
        "case_id": case.id,
        "document_id": document_id_for_case(case.id),
        **result,
    }


@router.post("/rebuild")
def rebuild_index(
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    result = sync.enqueue_rebuild(repo.list_cases())
    return {"collection": RETRIEVAL_COLLECTION, **result}


@router.get("/jobs")
def list_jobs(
    sync: Annotated[SyncService, Depends(get_sync_service)],
    collection: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    return {"items": sync.repository.list_jobs(collection, status, limit)}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    job = sync.repository.get(job_id)
    return job or {"error": "sync job not found"}


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    sync: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    job = sync.retry_job(job_id)
    return job or {"error": "sync job not found"}


@router.get("/status")
def sync_status(sync: Annotated[SyncService, Depends(get_sync_service)]) -> dict[str, object]:
    return sync.repository.status_summary(sync.settings.retrieval_collection)
