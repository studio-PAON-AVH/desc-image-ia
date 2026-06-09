# backend/descriptions/schemas.py
from typing import List, Optional
from pydantic import BaseModel


class DescriptionValidation(BaseModel):
    image_index: int
    text: str
    model: Optional[str] = None
    is_written_by_ai: bool
    is_written_by_human: bool


class DescriptionValidationRequest(BaseModel):
    validated_descriptions: List[DescriptionValidation]


class AddDescriptionsRequest(BaseModel):
    task_id_redis: str
