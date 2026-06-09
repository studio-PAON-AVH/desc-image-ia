import asyncio
from threading import Lock
import torch
from fastapi import FastAPI
from transformers import AutoProcessor, AutoModelForCausalLM
from utils import ImageRequest, ModelConfig, process_image

app = FastAPI()

torch.set_grad_enabled(False)

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
TORCH_DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

_model = None
_processor = None
_lock = Lock()

config = ModelConfig(
    task="<MORE_DETAILED_CAPTION>",
    device=DEVICE,
    dtype=TORCH_DTYPE,
    generate_kwargs={"max_new_tokens": 256, "num_beams": 1, "do_sample": False},
    use_batch_decode=True,
    skip_special_tokens=False,
    post_process=True,
)


def _get_model():
    global _model, _processor
    if _model is None:
        with _lock:
            if _model is None:
                _model = AutoModelForCausalLM.from_pretrained(
                    "microsoft/Florence-2-base", torch_dtype=TORCH_DTYPE, trust_remote_code=True, local_files_only=True
                ).to(DEVICE).eval()
                _processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True, local_files_only=True)
    return _processor, _model


@app.get("/")
def root():
    return {"status": "florence2_large model running"}


@app.post("/describe")
async def predict(request: ImageRequest):
    processor, model = _get_model()
    tasks = [process_image(image, processor, model, config) for image in request.images]
    image_list = await asyncio.gather(*tasks)
    return {"results": list(image_list)}
