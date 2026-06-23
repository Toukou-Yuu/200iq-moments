import time

from app.config import get_settings
from app.repositories.sync_job_repository import SyncJobRepository
from app.services.retrieval_client import RetrievalClient
from app.services.sync_service import SyncService


def main() -> None:
    settings = get_settings()
    repository = SyncJobRepository(settings.sync_db_path)
    service = SyncService(repository, settings)
    client = RetrievalClient(settings.retrieval_api_url)
    try:
        while True:
            service.process_due_jobs(client)
            time.sleep(settings.sync_worker_interval_seconds)
    finally:
        client.close()


if __name__ == "__main__":
    main()
