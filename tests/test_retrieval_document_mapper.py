from datetime import date, datetime, timezone

from app.models import CaseRecord, CaseStatus, GapAnalysis, Loss, LossType
from app.services.retrieval_document_mapper import (
    RETRIEVAL_COLLECTION,
    map_case_to_document,
)


def test_case_maps_to_retrieval_document():
    timestamp = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    case = CaseRecord(
        id="001",
        slug="airport-subscription",
        title="机场套餐误判",
        date=date(2025, 6, 20),
        status=CaseStatus.PUBLISHED,
        loss=Loss(
            amount=19.9,
            currency="CNY",
            types=[LossType.MONEY, LossType.DIGNITY],
        ),
        summary="看到价格划算就下单。",
        genius_logic="买！",
        reality="套餐一个月过期。",
        gap_analysis=[GapAnalysis(dimension="有效期", assumed="不限时", actual="一个月")],
        avoidance=["确认有效期"],
        checklist=["有效期是多久？"],
        mood="麻了",
        tags=["subscription"],
        created_at=timestamp,
        updated_at=timestamp,
    )

    document = map_case_to_document(case)

    assert RETRIEVAL_COLLECTION == "200iq_cases"
    assert document["id"] == "200iq:case:001"
    assert document["metadata"]["status"] == "published"
    assert document["metadata"]["loss_types"] == ["money", "dignity"]
    assert document["metadata"]["source_path"] == "data/cases/001-airport-subscription.md"
    assert "当时逻辑：买！" in document["text"]
    assert "差距分析：有效期：假设 不限时，实际 一个月" in document["text"]
