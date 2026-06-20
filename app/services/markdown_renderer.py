from decimal import Decimal

import yaml

from app.models import CaseRecord


def render_case_markdown(case: CaseRecord) -> str:
    frontmatter = {
        "id": case.id,
        "slug": case.slug,
        "title": case.title,
        "date": case.date.isoformat(),
        "status": case.status.value,
        "loss": case.loss.model_dump(mode="json") if case.loss else None,
        "tags": case.tags,
        "mood": case.mood,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
    }
    yaml_text = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

    lines = [
        "---",
        yaml_text.strip(),
        "---",
        "",
        f"## Case Study #{case.id} — {case.title}",
        "",
        f"**日期**：{case.date.isoformat()}  ",
        f"**损失金额**：{format_loss_amount(case)}  ",
        f"**损失类型**：{format_loss_types(case)}",
        "",
        "---",
        "",
        "### 事情经过",
        "",
        case.summary,
        "",
        "### 当时的天才逻辑",
        "",
        f"> \"{case.genius_logic}\"" if case.genius_logic else "> ",
        "",
        "### 现实情况",
        "",
        case.reality,
        "",
        "### 差距分析",
        "",
        "| 指标 | 我以为 | 实际上 |",
        "|------|--------|--------|",
    ]

    if case.gap_analysis:
        for item in case.gap_analysis:
            lines.append(f"| {item.dimension} | {item.assumed} | {item.actual} |")
    else:
        lines.append("| 无 | 无 | 无 |")

    lines.extend(
        [
            "",
            "### 本可以避免，如果我……",
            "",
        ]
    )
    lines.extend(f"- [ ] {item}" for item in case.avoidance)
    lines.extend(
        [
            "",
            "### 下次检查清单",
            "",
        ]
    )
    lines.extend(f"- [ ] {item}" for item in case.checklist)
    lines.extend(
        [
            "",
            "---",
            "",
            f"*复盘心情：{case.mood or ''}*",
            "",
        ]
    )
    return "\n".join(lines)


def format_loss_amount(case: CaseRecord) -> str:
    if not case.loss or case.loss.amount is None:
        return "无"
    amount = Decimal(str(case.loss.amount)).normalize()
    currency = case.loss.currency or "CNY"
    prefix = "¥" if currency == "CNY" else f"{currency} "
    return f"{prefix}{amount:f}"


def format_loss_types(case: CaseRecord) -> str:
    if not case.loss:
        return "无"
    if case.loss.description:
        return case.loss.description
    return " + ".join(loss_type.value for loss_type in case.loss.types) or "无"
