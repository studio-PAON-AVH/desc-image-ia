from pydantic import BaseModel
from typing import List, Optional, Any
from PIL import Image
from dataclasses import dataclass, field
import time
import requests
import io
import base64
from deep_translator import GoogleTranslator


class ImageRequest(BaseModel):
    images: List[str]
    translate_to_french: bool = False


@dataclass
class ModelConfig:
    task: Optional[str] = None
    device: str = "cpu"
    dtype: Any = None
    generate_kwargs: dict = field(default_factory=dict)
    use_pixel_values_only: bool = False
    use_batch_decode: bool = False
    skip_special_tokens: bool = True
    post_process: bool = False


async def process_image(image, processor, model, config: ModelConfig):
    try:
        if image.startswith(("http://", "https://")):
            raw_image = Image.open(requests.get(image, stream=True, timeout=10).raw).convert("RGB")
        else:
            image_bytes = base64.b64decode(image)
            raw_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        start = time.time()

        if config.use_pixel_values_only:
            pv = processor(images=raw_image, return_tensors="pt").pixel_values
            generated_ids = model.generate(pixel_values=pv, **config.generate_kwargs)
        elif config.task:
            inputs = processor(text=config.task, images=raw_image, return_tensors="pt")
            if config.dtype and config.device != "cpu":
                inputs = inputs.to(config.device, config.dtype)
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                **config.generate_kwargs,
            )
        else:
            inputs = processor(raw_image, return_tensors="pt")
            generated_ids = model.generate(**inputs, **config.generate_kwargs)

        if config.use_batch_decode:
            generated_text = processor.batch_decode(
                generated_ids, skip_special_tokens=config.skip_special_tokens
            )[0]
        else:
            generated_text = processor.decode(
                generated_ids[0], skip_special_tokens=config.skip_special_tokens
            )

        if config.post_process and config.task:
            parsed = processor.post_process_generation(
                generated_text, task=config.task, image_size=(raw_image.width, raw_image.height)
            )
            english_text = parsed[config.task]
        else:
            english_text = generated_text

        translation = GoogleTranslator(source="auto", target="fr").translate(english_text)
        end = time.time()

        return {
            "success": True,
            "english_description": english_text,
            "french_description": translation,
            "generation_time": end - start,
        }
    except TypeError as e:
        return {"error": f"Erreur lors de la génération de la description: {e}"}
