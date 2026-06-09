import asyncio
from threading import Lock
from fastapi import FastAPI
from transformers import BlipProcessor, BlipForConditionalGeneration
from utils import ImageRequest, ModelConfig, process_image

app = FastAPI()

_model = None
_processor = None
_lock = Lock()

config = ModelConfig()


def _get_model():
    global _model, _processor
    if _model is None:
        with _lock:
            if _model is None:
                _processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
                _model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
    return _processor, _model


@app.get("/")
def root():
    return {"status": "salesforce_cpu_large model running"}


@app.post("/describe")
async def predict(request: ImageRequest):
    processor, model = _get_model()
    tasks = [process_image(image, processor, model, config) for image in request.images]
    results = await asyncio.gather(*tasks)
    return {"results": list(results)}
