# backend/descriptions/schemas.py
from typing import List, Optional
from pydantic import BaseModel


class DescriptionValidation(BaseModel):
    image_index: int
    text: str
    model: Optional[str] = None


class DescriptionValidationRequest(BaseModel):
    validated_descriptions: List[DescriptionValidation]


class AddDescriptionsRequest(BaseModel):
    task_id_redis: str
