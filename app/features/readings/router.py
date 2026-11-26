from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/readings", tags=["readings"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/readings.md.
