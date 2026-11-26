from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/notifications", tags=["notifications"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/notifications.md.
