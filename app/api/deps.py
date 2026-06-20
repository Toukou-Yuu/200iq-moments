from app.config import get_settings
from app.repositories.case_repository import CaseRepository


def get_case_repository() -> CaseRepository:
    return CaseRepository(get_settings().data_dir)
