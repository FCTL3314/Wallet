import logging
from pathlib import Path

from faststream.redis import StreamSub

from wallet_sdk.messaging.schemas import ReportCompletedMsg, ReportRequestedMsg
from wallet_sdk.messaging.topics import REPORT_COMPLETED, REPORT_REQUESTED

from app.core.config import settings
from app.core.database import async_session
from app.messaging.broker import broker
from app.reports.excel import generate_account_export

logger = logging.getLogger(__name__)


@broker.subscriber(stream=StreamSub(REPORT_REQUESTED, group="report-service", consumer="report-service-1"))
@broker.publisher(stream=REPORT_COMPLETED)
async def handle_report_requested(msg: ReportRequestedMsg) -> ReportCompletedMsg:
    logger.info("Generating report job=%s user=%s", msg.job_id, msg.user_id)
    try:
        async with async_session() as db:
            excel_bytes = await generate_account_export(db, msg.user_id)
        output_path = Path(settings.REPORTS_DIR) / f"{msg.job_id}.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(excel_bytes)
        logger.info("Report saved to %s", output_path)
        return ReportCompletedMsg(job_id=msg.job_id)
    except Exception:
        logger.exception("Failed to generate report job=%s", msg.job_id)
        raise
