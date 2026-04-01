from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{job_id}/download")
async def download_report(job_id: str) -> FileResponse:
    file_path = Path(settings.REPORTS_DIR) / f"{job_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        path=str(file_path),
        filename=f"wallet-export-{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
