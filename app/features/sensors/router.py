from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/sensors", tags=["sensors"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/sensors.md.
