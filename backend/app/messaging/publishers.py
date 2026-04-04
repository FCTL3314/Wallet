from wallet_sdk.messaging.schemas import ReportRequestedMsg
from wallet_sdk.messaging.topics import REPORT_REQUESTED

from app.messaging.broker import broker


async def publish_report_requested(job_id: str, user_id: int) -> None:
    await broker.publish(
        ReportRequestedMsg(job_id=job_id, user_id=user_id),
        stream=REPORT_REQUESTED,
    )
