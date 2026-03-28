from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.models import User


def build_crud_router(
    model: type[Any],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    response_schema: type[BaseModel],
    prefix: str,
    tags: list[str],
    resource_name: str,
    id_param: str,
) -> APIRouter:
    """Return an APIRouter with standard list/create/update/delete endpoints.

    All operations are scoped to the authenticated user via get_current_user.
    Update and delete use get_or_404 to enforce both existence and ownership.
    Path parameters are extracted from the request by id_param name so that
    the generated OpenAPI schema shows the correct parameter name.
    """
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get("/", response_model=list[response_schema])
    async def list_resources(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        result = await db.execute(select(model).where(model.user_id == user.id))
        return result.scalars().all()

    @router.post(
        "/", response_model=response_schema, status_code=status.HTTP_201_CREATED
    )
    async def create_resource(
        body: create_schema,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        obj = model(**body.model_dump(), user_id=user.id)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    @router.put(f"/{{{id_param}}}", response_model=response_schema)
    async def update_resource(
        request: Request,
        body: update_schema,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        resource_id: int = int(request.path_params[id_param])
        obj = await get_or_404(db, model, resource_id, user.id, resource_name)
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await db.flush()
        await db.refresh(obj)
        return obj

    @router.delete(f"/{{{id_param}}}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_resource(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        resource_id: int = int(request.path_params[id_param])
        obj = await get_or_404(db, model, resource_id, user.id, resource_name)
        await db.delete(obj)

    return router
