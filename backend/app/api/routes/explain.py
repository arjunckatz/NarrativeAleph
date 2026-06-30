from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.explain.service import ExplainService
from app.schemas.explain import ExplainResponse

router = APIRouter(tags=["explain"])
DBSession = Depends(get_db)


@router.get("/explain", response_model=ExplainResponse)
def explain(
    ticker: Annotated[str, Query(min_length=1)],
    start_date: date | None = None,
    end_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
    db: Session = DBSession,
) -> ExplainResponse:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be before or equal to end_date",
        )

    return ExplainService(db).explain(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
