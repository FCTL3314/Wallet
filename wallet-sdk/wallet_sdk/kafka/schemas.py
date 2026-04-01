from pydantic import BaseModel


class ReportRequestedMsg(BaseModel):
    job_id: str
    user_id: int


class ReportCompletedMsg(BaseModel):
    job_id: str
