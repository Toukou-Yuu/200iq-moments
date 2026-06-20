from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["templates"])

REQUIRED_FIELDS = ["title", "date", "summary", "reality", "avoidance", "checklist"]
OPTIONAL_FIELDS = ["loss", "genius_logic", "gap_analysis", "mood", "tags"]
LOSS_TYPES = ["money", "time", "dignity", "opportunity", "energy", "other"]
STATUSES = ["draft", "published", "archived", "deleted"]

CASE_MARKDOWN_TEMPLATE = """---
id: ""
slug: ""
title: ""
date: ""
status: "published"
loss: null
tags: []
mood: null
created_at: ""
updated_at: ""
---

## Case Study #XXX - [标题]

**日期**：YYYY-MM-DD
**损失金额**：无
**损失类型**：无

---

### 事情经过

[发生了什么]

### 当时的天才逻辑

> "[当时的判断]"

### 现实情况

[实际上是怎么回事]

### 差距分析

| 指标 | 我以为 | 实际上 |
|------|--------|--------|
| ... | ... | ... |

### 本可以避免，如果我……

- [ ] [预防措施]

### 下次检查清单

- [ ] [检查项]

---

*复盘心情：*
"""


@router.get("/case")
def case_template() -> dict[str, object]:
    return {
        "version": "1.0",
        "format": "case-json",
        "required_fields": REQUIRED_FIELDS,
        "optional_fields": OPTIONAL_FIELDS,
        "enums": {
            "loss.types": LOSS_TYPES,
            "status": STATUSES,
        },
        "schema": {
            "title": "string",
            "date": "YYYY-MM-DD",
            "loss": {
                "amount": "number|null",
                "currency": "string|null",
                "types": ["string"],
                "description": "string|null",
            },
            "summary": "string",
            "genius_logic": "string|null",
            "reality": "string",
            "gap_analysis": [
                {
                    "dimension": "string",
                    "assumed": "string",
                    "actual": "string",
                }
            ],
            "avoidance": ["string"],
            "checklist": ["string"],
            "mood": "string|null",
            "tags": ["string"],
        },
    }


@router.get("/case/markdown")
def case_markdown_template() -> dict[str, str]:
    return {
        "version": "1.0",
        "format": "markdown",
        "content": CASE_MARKDOWN_TEMPLATE,
    }
