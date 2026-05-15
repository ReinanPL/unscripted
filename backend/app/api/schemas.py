from typing import Literal

from pydantic import BaseModel, Field


class CampaignCreateResponse(BaseModel):
    campaign_id: str


class ActionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ActionEvent(BaseModel):
    type: Literal["chunk", "done", "error"]
    text: str = ""
