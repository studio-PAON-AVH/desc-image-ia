from pydantic import BaseModel
from typing import List

class ImageRequest(BaseModel):
    images: List[str]
    translate_to_french: bool = False
    
class EPUBRequest(BaseModel):
    epub_path: str