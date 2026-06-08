from PIL import Image
import requests, time
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from deep_translator import GoogleTranslator
from models.image_request import ImageRequest
from fastapi import FastAPI

app=FastAPI()

processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained(
    "Salesforce/blip2-opt-2.7b"
)

@app.get("/")
def root():
    return {"status": "blip2 model running"}

@app.post("/describe")
def predict(request: ImageRequest):
    return describe_with_blip2(request.image)

def describe_with_blip2(image_path_or_url, output_file=None):

    if image_path_or_url.startswith(('http://', 'https://')):
        try:
            raw_image = Image.open(requests.get(image_path_or_url, stream=True).raw).convert('RGB')
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors du téléchargement de l'image: {e}"
            }
    else:
        try:
            raw_image = Image.open(image_path_or_url).convert('RGB')
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors de l'ouverture de l'image locale: {e}"
            }

    try:
        inputs = processor(raw_image, return_tensors="pt")
        start = time.time()
        generated_ids = model.generate(**inputs)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
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