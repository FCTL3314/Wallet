from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFound

T = TypeVar("T")


async def get_or_404(
    db: AsyncSession,
    model: type[T],
    resource_id: int,
    user_id: int,
    resource_type: str,
    options: list[Any] | None = None,
) -> T:
    q = select(model).where(model.id == resource_id, model.user_id == user_id)
    if options:
        q = q.options(*options)
    result = await db.execute(q)
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound(resource_type)
    return obj
