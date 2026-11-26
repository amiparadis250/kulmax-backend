from fastapi import APIRouter

from app.core.errors import ERROR_RESPONSES

router = APIRouter(prefix="/orders", tags=["orders"], responses=ERROR_RESPONSES)

# Not implemented yet. See docs/specs/orders.md.
