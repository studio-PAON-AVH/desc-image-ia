from transformers import AutoProcessor, AutoModelForCausalLM
import requests, json, time
from PIL import Image
from deep_translator import GoogleTranslator
from fastapi import FastAPI
from models.image_request import ImageRequest

app = FastAPI()

@app.get("/")
def root():
    return {"status": "git_large model running"}

@app.post("/describe")
def predict(request: ImageRequest):
    return describe_image_with_git_large(request.image)

def describe_image_with_git_large(image, output_file=None):
    processor = AutoProcessor.from_pretrained("microsoft/git-large")
    model = AutoModelForCausalLM.from_pretrained("microsoft/git-large")

    start = time.time()
    raw_image = None
    if image.startswith(('http://', 'https://')):
        try:
            raw_image = Image.open(requests.get(image, stream=True).raw).convert('RGB')
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors du téléchargement de l'image: {e}"
            }
    else:
        try:
            raw_image = Image.open(image).convert('RGB')
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors de l'ouverture de l'image locale: {e}"
            }

    try:
        pixel_values = processor(images=raw_image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values=pixel_values, max_length=50)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        translation = GoogleTranslator(source='auto', target='fr').translate(generated_text)
        end = time.time()
        return {
            "success": True,
            "english_description": generated_text,
            "french_description": translation,
            "generation_time": end - start
        }
    except Exception as e:
        return {
            "success": False,
            "english_description": None,
            "french_description": None,
            "error": f"Model error: {e}"
        }
