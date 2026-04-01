from wallet_sdk.kafka.schemas import ReportRequestedMsg
from wallet_sdk.kafka.topics import REPORT_REQUESTED

from app.kafka.broker import broker


async def publish_report_requested(job_id: str, user_id: int) -> None:
    await broker.publish(
        ReportRequestedMsg(job_id=job_id, user_id=user_id),
        topic=REPORT_REQUESTED,
    )
