from app.config import get_settings
from app.repositories.case_repository import CaseRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.services.sync_service import SyncService


def get_case_repository() -> CaseRepository:
    return CaseRepository(get_settings().data_dir)


def get_sync_job_repository() -> SyncJobRepository:
    return SyncJobRepository(get_settings().sync_db_path)


def get_sync_service() -> SyncService:
    return SyncService(get_sync_job_repository(), get_settings())
