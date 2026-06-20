from fastapi import APIRouter

from app.api import system, templates


router = APIRouter(prefix="/v1")
router.include_router(system.router)
router.include_router(templates.router)
