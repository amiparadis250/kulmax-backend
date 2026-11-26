from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/dashboard", tags=["dashboard"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/dashboard.md.
