from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.case_repository import CaseRepository
from app.services.stats_service import summary, timeline

from .deps import get_case_repository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def stats_summary(repo: Annotated[CaseRepository, Depends(get_case_repository)]) -> dict[str, object]:
    return summary(repo.list_cases())


@router.get("/timeline")
def stats_timeline(repo: Annotated[CaseRepository, Depends(get_case_repository)]) -> dict[str, object]:
    return timeline(repo.list_cases())
