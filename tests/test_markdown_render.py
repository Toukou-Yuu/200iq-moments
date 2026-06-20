from datetime import date, datetime

from app.models import CaseRecord, GapAnalysis, Loss
from app.services.markdown_parser import parse_case_markdown
from app.services.markdown_renderer import render_case_markdown


def make_case() -> CaseRecord:
    now = datetime.fromisoformat("2025-06-20T12:00:00+08:00")
    return CaseRecord(
        id="001",
        slug="airport-subscription",
        title="买限时机场套餐以为不限时",
        date=date.fromisoformat("2025-06-20"),
        loss=Loss(
            amount=19.9,
            currency="CNY",
            types=["money", "dignity"],
            description="金钱 + 尊严",
        ),
        summary="购买机场订阅时，看到单位数据价格划算，立即下单付款。",
        genius_logic="150G才19.9，每元7.5G，比之前买的6.5G/元还划算，买！",
        reality="本次套餐限时一个月，未用完流量月底过期。",
        gap_analysis=[
            GapAnalysis(dimension="有效期", assumed="不限时", actual="一个月")
        ],
        avoidance=["在付款前确认有效期"],
        checklist=["有效期是多久？限时 or 不限时？"],
        mood="麻了",
        tags=["subscription"],
        created_at=now,
        updated_at=now,
    )


def test_case_json_renders_to_markdown():
    markdown = render_case_markdown(make_case())

    assert markdown.startswith("---\n")
    assert "## Case Study #001" in markdown
    assert "| 有效期 | 不限时 | 一个月 |" in markdown


def test_frontmatter_markdown_parses_back_to_case():
    original = make_case()
    parsed = parse_case_markdown(render_case_markdown(original))

    assert parsed.warnings == []
    assert parsed.case is not None
    assert parsed.case.id == original.id
    assert parsed.case.title == original.title
    assert parsed.case.checklist == original.checklist


def test_legacy_markdown_parses_required_fields():
    content = """## Case Study #001 — 买限时机场套餐以为不限时

**日期**：2025-06-20
**损失金额**：¥19.9
**损失类型**：💸 金钱 + 🫡 尊严

### 事情经过

购买机场订阅时，看到单位数据价格划算，立即下单付款。

### 当时的天才逻辑

> "买！"

### 现实情况

月底过期。

### 差距分析

| 指标 | 我以为 | 实际上 |
|------|--------|--------|
| 有效期 | 不限时 | 一个月 |

### 本可以避免，如果我……

- [ ] 在付款前确认有效期

### 下次检查清单

- [ ] 有效期是多久？

---

*复盘心情：麻了*
"""

    parsed = parse_case_markdown(content)

    assert parsed.case is not None
    assert parsed.case.id == "001"
    assert parsed.case.loss is not None
    assert parsed.case.loss.amount == 19.9
    assert parsed.case.avoidance == ["在付款前确认有效期"]
