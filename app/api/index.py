from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.case_repository import CaseRepository

from .deps import get_case_repository

router = APIRouter(prefix="/index", tags=["index"])


@router.post("/sync")
def sync_index(
    payload: dict,
    repo: Annotated[CaseRepository, Depends(get_case_repository)],
) -> dict[str, object]:
    since = payload.get("since")
    since_dt = datetime.fromisoformat(since) if since else None
    events = []
    for case in repo.list_cases():
        if since_dt is None or case.updated_at >= since_dt:
            events.append(
                {
                    "type": "case.updated",
                    "case_id": case.id,
                    "updated_at": case.updated_at.isoformat(),
                }
            )
    return {"events": events}


@router.post("/rebuild")
def rebuild_index(repo: Annotated[CaseRepository, Depends(get_case_repository)]) -> dict[str, object]:
    items = []
    for case in repo.list_cases():
        items.append(
            {
                "case_id": case.id,
                "source": "200iq-moments",
                "doc_type": "case",
                "title": case.title,
                "text": "\n".join(
                    item
                    for item in [
                        case.summary,
                        case.genius_logic or "",
                        case.reality,
                        "\n".join(case.avoidance),
                        "\n".join(case.checklist),
                    ]
                    if item
                ),
                "metadata": {
                    "date": case.date.isoformat(),
                    "tags": case.tags,
                    "loss_types": [loss_type.value for loss_type in case.loss.types]
                    if case.loss
                    else [],
                },
            }
        )
    return {"items": items}
