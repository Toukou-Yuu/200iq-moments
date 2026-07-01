from datetime import date

from app.models import CaseCreate, CaseUpdate
from app.repositories.case_repository import CaseRepository


def test_repository_creates_and_reads_case(tmp_path):
    repo = CaseRepository(tmp_path)
    case = repo.create_case(
        CaseCreate(
            title="机场套餐误判",
            date=date.fromisoformat("2025-06-20"),
            summary="看到单位价格划算就下单。",
            reality="套餐一个月过期。",
            avoidance=["确认有效期"],
            checklist=["有效期是多久？"],
            tags=["subscription"],
        )
    )

    assert case.id == "001"
    assert repo.get_case("001").title == "机场套餐误判"
    assert (tmp_path / "index.json").exists()


def test_repository_updates_case(tmp_path):
    repo = CaseRepository(tmp_path)
    created = repo.create_case(
        CaseCreate(
            title="机场套餐误判",
            date=date.fromisoformat("2025-06-20"),
            summary="看到单位价格划算就下单。",
            reality="套餐一个月过期。",
            avoidance=["确认有效期"],
            checklist=["有效期是多久？"],
        )
    )

    updated, fields = repo.update_case(created.id, CaseUpdate(tags=["subscription"]))

    assert fields == ["tags"]
    assert updated.tags == ["subscription"]


def test_repository_imports_legacy_markdown(tmp_path):
    repo = CaseRepository(tmp_path)
    content = """## Case Study #001 — 机场套餐误判

**日期**：2025-06-20

### 事情经过

看到单位价格划算就下单。

### 现实情况

套餐一个月过期。

### 本可以避免，如果我……

- [ ] 确认有效期

### 下次检查清单

- [ ] 有效期是多久？
"""

    record, created, updated, warnings = repo.import_markdown(content)

    assert record.id == "001"
    assert created is True
    assert updated is False
    assert warnings == ["slug could not be inferred from title"]
