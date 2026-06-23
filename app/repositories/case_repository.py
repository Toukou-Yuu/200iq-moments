import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.models import CaseCreate, CaseRecord, CaseStatus, CaseUpdate
from app.services.markdown_parser import parse_case_markdown
from app.services.markdown_renderer import render_case_markdown
from app.services.slug import slugify


class CaseNotFoundError(Exception):
    pass


class CaseAlreadyExistsError(Exception):
    pass


class InvalidMarkdownError(Exception):
    def __init__(self, warnings: list[str]) -> None:
        super().__init__("Invalid markdown")
        self.warnings = warnings


class CaseRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.cases_dir = data_dir / "cases"
        self.index_path = data_dir / "index.json"
        self.cases_dir.mkdir(parents=True, exist_ok=True)

    def list_cases(
        self,
        status: CaseStatus | None = None,
        loss_type: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "date_desc",
    ) -> list[CaseRecord]:
        cases = self._read_all_cases()
        if status is None:
            cases = [case for case in cases if case.status != CaseStatus.DELETED]
        else:
            cases = [case for case in cases if case.status == status]
        if loss_type:
            cases = [
                case
                for case in cases
                if case.loss and loss_type in [item.value for item in case.loss.types]
            ]
        if tag:
            cases = [case for case in cases if tag in case.tags]
        if q:
            cases = [
                case
                for case in cases
                if q in case.title or q in case.summary or q in case.reality
            ]
        if date_from:
            cases = [case for case in cases if case.date.isoformat() >= date_from]
        if date_to:
            cases = [case for case in cases if case.date.isoformat() <= date_to]
        return sort_cases(cases, sort)

    def get_case(self, case_id: str) -> CaseRecord:
        path = self._path_for_id(case_id)
        if not path:
            raise CaseNotFoundError(case_id)
        return self._read_case(path)

    def create_case(self, case: CaseCreate) -> CaseRecord:
        case_id = self.next_id()
        now = datetime.now().astimezone()
        record = CaseRecord(
            **case.model_dump(),
            id=case_id,
            slug=slugify(case.title),
            created_at=now,
            updated_at=now,
        )
        path = self.case_path(record)
        if path.exists():
            raise CaseAlreadyExistsError(case_id)
        self._write_case(record)
        self.rebuild_index()
        return record

    def update_case(self, case_id: str, patch: CaseUpdate) -> tuple[CaseRecord, list[str]]:
        current = self.get_case(case_id)
        update_data = patch.model_dump(exclude_unset=True)
        current_data = current.model_dump()
        updated_fields = [
            field for field, value in update_data.items() if current_data[field] != value
        ]
        if not updated_fields:
            return current, []
        merged = current.model_dump()
        merged.update({field: update_data[field] for field in updated_fields})
        merged["updated_at"] = datetime.now().astimezone()
        if "title" in update_data:
            merged["slug"] = slugify(update_data["title"])
        record = CaseRecord.model_validate(merged)
        old_path = self.case_path(current)
        new_path = self.case_path(record)
        if old_path != new_path and old_path.exists():
            old_path.unlink()
        self._write_case(record)
        self.rebuild_index()
        return record, updated_fields

    def archive_case(self, case_id: str, status: CaseStatus = CaseStatus.ARCHIVED) -> CaseRecord:
        record, _ = self.update_case(case_id, CaseUpdate(status=status))
        return record

    def render_markdown(self, case_id: str) -> str:
        return render_case_markdown(self.get_case(case_id))

    def import_markdown(self, content: str, mode: str = "upsert") -> tuple[CaseRecord, bool, bool, list[str]]:
        parsed = parse_case_markdown(content)
        if parsed.case is None:
            raise InvalidMarkdownError(parsed.warnings)
        record = parsed.case
        existing_path = self._path_for_id(record.id) if record.id else None
        created = existing_path is None
        if existing_path and mode == "create":
            raise CaseAlreadyExistsError(record.id)
        if not record.id:
            record = record.model_copy(update={"id": self.next_id()})
        if not record.slug:
            record = record.model_copy(update={"slug": slugify(record.title)})
        self._write_case(record)
        self.rebuild_index()
        return record, created, not created, parsed.warnings

    def rebuild_index(self) -> list[dict[str, object]]:
        items = [case_summary(case) for case in self._read_all_cases()]
        payload = {
            "items": items,
            "total": len(items),
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return items

    def list_all_cases(self) -> list[CaseRecord]:
        return sort_cases(self._read_all_cases(), "date_desc")

    def next_id(self) -> str:
        max_id = 0
        for case in self._read_all_cases():
            if case.id.isdigit():
                max_id = max(max_id, int(case.id))
        return f"{max_id + 1:03d}"

    def case_path(self, case: CaseRecord) -> Path:
        return self.cases_dir / f"{case.id}-{case.slug}.md"

    def _read_all_cases(self) -> list[CaseRecord]:
        return [self._read_case(path) for path in sorted(self.cases_dir.glob("*.md"))]

    def _read_case(self, path: Path) -> CaseRecord:
        parsed = parse_case_markdown(path.read_text())
        if parsed.case is None:
            raise InvalidMarkdownError(parsed.warnings)
        return parsed.case

    def _write_case(self, case: CaseRecord) -> None:
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        self.case_path(case).write_text(render_case_markdown(case))

    def _path_for_id(self, case_id: str) -> Path | None:
        matches = list(self.cases_dir.glob(f"{case_id}-*.md"))
        return matches[0] if matches else None


def sort_cases(cases: Iterable[CaseRecord], sort: str) -> list[CaseRecord]:
    reverse = sort in {"date_desc", "created_desc", "updated_desc"}
    key_map = {
        "date_desc": lambda case: case.date,
        "date_asc": lambda case: case.date,
        "created_desc": lambda case: case.created_at,
        "updated_desc": lambda case: case.updated_at,
    }
    return sorted(cases, key=key_map.get(sort, key_map["date_desc"]), reverse=reverse)


def case_summary(case: CaseRecord) -> dict[str, object]:
    loss = case.loss.model_dump(mode="json") if case.loss else None
    return {
        "id": case.id,
        "slug": case.slug,
        "title": case.title,
        "date": case.date.isoformat(),
        "status": case.status.value,
        "loss": loss,
        "tags": case.tags,
        "updated_at": case.updated_at.isoformat(),
    }
