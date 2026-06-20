from collections import Counter, defaultdict

from app.models import CaseRecord, CaseStatus


def summary(cases: list[CaseRecord]) -> dict[str, object]:
    status_count = Counter(case.status.value for case in cases)
    loss_by_currency: dict[str, float] = defaultdict(float)
    loss_type_count = Counter()
    tag_count = Counter()
    for case in cases:
        tag_count.update(case.tags)
        if case.loss:
            if case.loss.amount is not None and case.loss.currency:
                loss_by_currency[case.loss.currency] += case.loss.amount
            loss_type_count.update(loss_type.value for loss_type in case.loss.types)

    return {
        "total_cases": len(cases),
        "status_count": {status.value: status_count.get(status.value, 0) for status in CaseStatus},
        "total_loss": dict(loss_by_currency),
        "loss_type_count": {
            loss_type: loss_type_count.get(loss_type, 0)
            for loss_type in ["money", "time", "dignity", "opportunity", "energy", "other"]
        },
        "top_tags": [
            {"tag": tag, "count": count} for tag, count in tag_count.most_common(10)
        ],
        "latest_case_date": max((case.date.isoformat() for case in cases), default=None),
    }


def timeline(cases: list[CaseRecord]) -> dict[str, object]:
    months: dict[str, dict[str, object]] = {}
    for case in cases:
        month = case.date.isoformat()[:7]
        item = months.setdefault(month, {"month": month, "case_count": 0, "loss": {}})
        item["case_count"] = int(item["case_count"]) + 1
        if case.loss and case.loss.amount is not None and case.loss.currency:
            loss = item["loss"]
            loss[case.loss.currency] = loss.get(case.loss.currency, 0) + case.loss.amount
    return {"items": [months[month] for month in sorted(months)]}
