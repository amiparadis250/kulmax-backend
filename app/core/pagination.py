"""Shared pagination: `PageParams` dependency and the `Page[T]` response shape."""

from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel


@dataclass(frozen=True)
class PageParams:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def page_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PageParams:
    return PageParams(page=page, limit=limit)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int
