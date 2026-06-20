from fastapi import APIRouter

from app.api import cases, import_export, index, stats, system, templates


router = APIRouter(prefix="/v1")
router.include_router(system.router)
router.include_router(templates.router)
router.include_router(cases.router)
router.include_router(import_export.router)
router.include_router(stats.router)
router.include_router(index.router)
