import asyncio
from threading import Lock
import torch
from fastapi import FastAPI
from transformers import AutoProcessor, AutoModelForCausalLM
from utils import ImageRequest, ModelConfig, process_image

app = FastAPI()

torch.set_grad_enabled(False)

_model = None
_processor = None
_lock = Lock()

config = ModelConfig(
    use_pixel_values_only=True,
    use_batch_decode=True,
    generate_kwargs={"max_length": 50, "num_beams": 1, "do_sample": False},
)


def _get_model():
    global _model, _processor
    if _model is None:
        with _lock:
            if _model is None:
                _processor = AutoProcessor.from_pretrained("microsoft/git-large", local_files_only=True)
                _model = AutoModelForCausalLM.from_pretrained("microsoft/git-large", local_files_only=True).eval()
    return _processor, _model


@app.get("/")
def root():
    return {"status": "git_large model running"}


@app.post("/describe")
async def predict(request: ImageRequest):
    processor, model = _get_model()
    tasks = [process_image(image, processor, model, config) for image in request.images]
    image_list = await asyncio.gather(*tasks)
    return {"results": list(image_list)}
