from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": __version__,
    }


@router.get("/info")
def info() -> dict[str, object]:
    settings = get_settings()
    cases_dir = settings.data_dir / "cases"
    case_count = len(list(cases_dir.glob("*.md"))) if cases_dir.exists() else 0
    return {
        "name": settings.service_name,
        "description": settings.service_description,
        "api_version": settings.api_version,
        "case_count": case_count,
        "storage": "markdown-frontmatter",
        "auth_enabled": settings.auth_enabled,
    }
