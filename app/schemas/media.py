from pydantic import BaseModel
from datetime import datetime


class MediaOut(BaseModel):
    id: int
    owner_id: int
    url: str
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}