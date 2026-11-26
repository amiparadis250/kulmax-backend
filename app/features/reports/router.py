from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/reports", tags=["reports"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/reports.md.
