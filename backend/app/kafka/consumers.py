import json
import logging

from wallet_sdk.kafka.schemas import ReportCompletedMsg
from wallet_sdk.kafka.topics import REPORT_COMPLETED

from app.core.redis import get_redis
from app.kafka.broker import broker

logger = logging.getLogger(__name__)


@broker.subscriber(REPORT_COMPLETED)
async def handle_report_completed(msg: ReportCompletedMsg) -> None:
    r = get_redis()
    key = f"report:{msg.job_id}"
    raw = await r.get(key)
    if raw:
        data = json.loads(raw)
        data["status"] = "ready"
        await r.set(key, json.dumps(data), ex=3600)
        logger.info("Report %s marked as ready", msg.job_id)
    else:
        logger.warning("Report %s not found in Redis on completion", msg.job_id)
