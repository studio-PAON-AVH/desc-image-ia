from pydantic import BaseModel

class ImageRequest(BaseModel):
    image: str
    translate_to_french: bool = False