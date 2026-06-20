import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import yaml

from app.models import CaseRecord
from app.services.slug import slugify


@dataclass
class ParsedCase:
    case: CaseRecord | None
    warnings: list[str] = field(default_factory=list)


def parse_case_markdown(content: str) -> ParsedCase:
    if content.startswith("---\n"):
        return parse_frontmatter_markdown(content)
    return parse_legacy_markdown(content)


def parse_frontmatter_markdown(content: str) -> ParsedCase:
    _, frontmatter_text, body = content.split("---", 2)
    data = yaml.safe_load(frontmatter_text) or {}
    sections = extract_sections(body)
    payload = {
        "id": str(data.get("id") or ""),
        "slug": data.get("slug") or slugify(data.get("title") or ""),
        "title": data.get("title") or parse_title(body),
        "date": data.get("date"),
        "status": data.get("status") or "published",
        "loss": data.get("loss"),
        "summary": sections.get("事情经过") or "",
        "genius_logic": strip_quote(sections.get("当时的天才逻辑")),
        "reality": sections.get("现实情况") or "",
        "gap_analysis": parse_gap_table(sections.get("差距分析") or ""),
        "avoidance": parse_checklist(sections.get("本可以避免，如果我……") or ""),
        "checklist": parse_checklist(
            sections.get("下次检查清单") or find_section_by_prefix(sections, "下次") or ""
        ),
        "mood": data.get("mood") or parse_mood(body),
        "tags": data.get("tags") or [],
        "created_at": data.get("created_at") or datetime.now().astimezone().isoformat(),
        "updated_at": data.get("updated_at") or datetime.now().astimezone().isoformat(),
    }
    try:
        return ParsedCase(case=CaseRecord.model_validate(payload))
    except Exception as exc:
        return ParsedCase(case=None, warnings=[str(exc)])


def parse_legacy_markdown(content: str) -> ParsedCase:
    sections = extract_sections(content)
    title = parse_title(content)
    payload: dict[str, Any] = {
        "id": parse_id(content) or "",
        "slug": slugify(title),
        "title": title,
        "date": parse_inline_value(content, "日期"),
        "status": "published",
        "loss": parse_loss(content),
        "summary": sections.get("事情经过") or "",
        "genius_logic": strip_quote(sections.get("当时的天才逻辑")),
        "reality": sections.get("现实情况") or "",
        "gap_analysis": parse_gap_table(sections.get("差距分析") or ""),
        "avoidance": parse_checklist(sections.get("本可以避免，如果我……") or ""),
        "checklist": parse_checklist(find_section_by_prefix(sections, "下次") or ""),
        "mood": parse_mood(content),
        "tags": [],
        "created_at": datetime.now().astimezone().isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
    }
    warnings = []
    if payload["slug"] == "case":
        warnings.append("slug could not be inferred from title")
    try:
        return ParsedCase(case=CaseRecord.model_validate(payload), warnings=warnings)
    except Exception as exc:
        return ParsedCase(case=None, warnings=warnings + [str(exc)])


def extract_sections(content: str) -> dict[str, str]:
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", content, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections[match.group(1).strip()] = content[start:end].strip()
    return sections


def find_section_by_prefix(sections: dict[str, str], prefix: str) -> str | None:
    for title, body in sections.items():
        if title.startswith(prefix) and "检查清单" in title:
            return body
    return None


def parse_title(content: str) -> str:
    match = re.search(r"^##\s+Case Study #\d+\s+[—-]\s+(.+?)\s*$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_id(content: str) -> str | None:
    match = re.search(r"^##\s+Case Study #(\d+)", content, re.MULTILINE)
    return match.group(1) if match else None


def parse_inline_value(content: str, label: str) -> str | None:
    match = re.search(rf"\*\*{re.escape(label)}\*\*：(.+)", content)
    return match.group(1).strip() if match else None


def parse_loss(content: str) -> dict[str, Any] | None:
    amount_text = parse_inline_value(content, "损失金额")
    type_text = parse_inline_value(content, "损失类型")
    amount = None
    if amount_text:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", amount_text)
        amount = float(match.group(1)) if match else None
    loss_types = []
    if type_text:
        if "金钱" in type_text:
            loss_types.append("money")
        if "时间" in type_text:
            loss_types.append("time")
        if "尊严" in type_text:
            loss_types.append("dignity")
    if amount is None and not loss_types and not type_text:
        return None
    return {
        "amount": amount,
        "currency": "CNY" if amount is not None else None,
        "types": loss_types,
        "description": clean_markdown(type_text) if type_text else None,
    }


def parse_gap_table(content: str) -> list[dict[str, str]]:
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "指标" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 3:
            rows.append({"dimension": cells[0], "assumed": cells[1], "actual": cells[2]})
    return rows


def parse_checklist(content: str) -> list[str]:
    items = []
    for line in content.splitlines():
        match = re.match(r"^-\s+\[[ xX]?\]\s+(.+)$", line.strip())
        if match:
            items.append(clean_markdown(match.group(1).strip()))
    return items


def strip_quote(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    value = re.sub(r"^>\s*", "", value).strip()
    return value.strip('"') or None


def parse_mood(content: str) -> str | None:
    match = re.search(r"\*复盘心情：(.+?)\*", content)
    return clean_markdown(match.group(1).strip()) if match else None


def clean_markdown(value: str) -> str:
    return value.replace("**", "").replace("💸", "").replace("⏰", "").replace("🫡", "").strip()
