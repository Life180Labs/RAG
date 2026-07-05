"""Cache stats endpoint (docs/05-task.md Phase 17; docs/02-architecture.md
section 148's "Cache Hit Ratio" metric).

Authenticated but not tenant-scoped — like `/llm/models`, this describes
the caching *system* itself (hit/miss counts per cache type), not any one
repository's data, so there is no RBAC dependency beyond being logged in.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.core.cache import metrics
from app.models.user import User
from app.schemas.cache import CacheStatsRead
from app.schemas.common import SuccessResponse

router = APIRouter(tags=["cache"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.get("/cache/stats", response_model=SuccessResponse[CacheStatsRead])
async def get_cache_stats(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[CacheStatsRead]:
    stats = await metrics.get_stats()
    return SuccessResponse(
        data=CacheStatsRead.model_validate(stats), request_id=_request_id(request)
    )
