import json
import uuid
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import get_current_user, get_redis
from app.kafka.publishers import publish_report_requested
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/export")
async def request_export(
    user: User = Depends(get_current_user),
    r: aioredis.Redis = Depends(get_redis),
):
    job_id = str(uuid.uuid4())
    await r.set(
        f"report:{job_id}",
        json.dumps({"status": "pending", "user_id": user.id}),
        ex=3600,
    )
    await publish_report_requested(job_id, user.id)
    return {"job_id": job_id}


@router.get("/export/{job_id}/status")
async def get_export_status(
    job_id: str,
    user: User = Depends(get_current_user),
    r: aioredis.Redis = Depends(get_redis),
):
    raw = await r.get(f"report:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    data = json.loads(raw)
    if data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"status": data["status"]}


@router.get("/export/{job_id}/download")
async def download_export(
    job_id: str,
    user: User = Depends(get_current_user),
    r: aioredis.Redis = Depends(get_redis),
):
    raw = await r.get(f"report:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    data = json.loads(raw)
    if data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if data["status"] != "ready":
        raise HTTPException(status_code=409, detail="Report not ready yet")
    file_path = Path(settings.REPORTS_DIR) / f"{job_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(
        path=str(file_path),
        filename=f"wallet-export-{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
