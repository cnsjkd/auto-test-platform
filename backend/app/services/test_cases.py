from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TestCase
from app.schemas.contracts import TestCaseCreateRequest, derive_pixel_fallback_stats


class TestCaseService:
    def list_cases(
        self,
        db: Session,
        *,
        type_: str | None = None,
        tags: str | None = None,
        enabled: bool | None = None,
    ) -> list[TestCase]:
        query = select(TestCase).order_by(TestCase.updated_at.desc(), TestCase.id.desc())
        if type_:
            query = query.where(TestCase.type == type_)
        if enabled is not None:
            query = query.where(TestCase.status == ("enabled" if enabled else "disabled"))
        cases = list(db.scalars(query).all())
        if tags:
            required = {tag.strip() for tag in tags.split(",") if tag.strip()}
            cases = [case for case in cases if required.issubset(set(case.tags or []))]
        return cases

    def create_case(self, db: Session, request: TestCaseCreateRequest) -> TestCase:
        has_pixel_fallback, pixel_fallback_count = derive_pixel_fallback_stats(request.steps)
        case = TestCase(
            name=request.name,
            type=request.type,
            priority=request.priority,
            tags=request.tags,
            status=request.status,
            steps=request.steps,
            has_pixel_fallback=has_pixel_fallback,
            pixel_fallback_count=pixel_fallback_count,
            description=request.description,
        )
        db.add(case)
        db.flush()
        return case
