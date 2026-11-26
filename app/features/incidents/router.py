from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/incidents", tags=["incidents"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/incidents.md.
