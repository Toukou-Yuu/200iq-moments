from __future__ import annotations

from app.models import CaseRecord


RETRIEVAL_COLLECTION = "200iq_cases"


def document_id_for_case(case_id: str) -> str:
    return f"200iq:case:{case_id}"


def map_case_to_document(case: CaseRecord) -> dict[str, object]:
    loss_types = [loss_type.value for loss_type in case.loss.types] if case.loss else []
    metadata = {
        "case_id": case.id,
        "slug": case.slug,
        "status": case.status.value,
        "date": case.date.isoformat(),
        "tags": case.tags,
        "loss_amount": case.loss.amount if case.loss else None,
        "loss_currency": case.loss.currency if case.loss else None,
        "loss_types": loss_types,
        "source_path": f"data/cases/{case.id}-{case.slug}.md",
        "updated_at": case.updated_at.isoformat(),
    }
    return {
        "id": document_id_for_case(case.id),
        "source": "200iq-moments",
        "doc_type": "case",
        "title": case.title,
        "text": build_search_text(case, loss_types),
        "metadata": metadata,
        "updated_at": case.updated_at.isoformat(),
    }


def build_search_text(case: CaseRecord, loss_types: list[str] | None = None) -> str:
    loss_types = loss_types if loss_types is not None else [
        loss_type.value for loss_type in case.loss.types
    ] if case.loss else []
    loss = "无"
    if case.loss and case.loss.amount is not None:
        currency = case.loss.currency or "CNY"
        loss = f"{case.loss.amount} {currency}"
    if loss_types:
        loss = f"{loss}；{', '.join(loss_types)}"

    gap_analysis = "；".join(
        f"{item.dimension}：假设 {item.assumed}，实际 {item.actual}"
        for item in case.gap_analysis
    ) or "无"
    return "\n".join(
        [
            f"标题：{case.title}",
            f"日期：{case.date.isoformat()}",
            f"损失：{loss}",
            f"摘要：{case.summary}",
            f"当时逻辑：{case.genius_logic or '无'}",
            f"现实情况：{case.reality}",
            f"差距分析：{gap_analysis}",
            f"避免方式：{'；'.join(case.avoidance)}",
            f"下次检查清单：{'；'.join(case.checklist)}",
            f"复盘心情：{case.mood or '无'}",
            f"标签：{', '.join(case.tags) or '无'}",
        ]
    )
