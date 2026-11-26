from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/vehicles", tags=["vehicles"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/vehicles.md.
