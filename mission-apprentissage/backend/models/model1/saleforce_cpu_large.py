#Running the model on CPU
import requests, time, sys, json
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from deep_translator import GoogleTranslator
from backend.utils.image_request import ImageRequest
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root(): 
    return {"status": "salesforce_cpu_large model running"}

@app.post("/describe")
def predict(request: ImageRequest):
    return describe_with_salesforce_cpu_large(request.image)

def describe_with_salesforce_cpu_large(image_path_or_url, output_file=None):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

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
        start = time.time()
        # description non guidée (sans prompt)
        inputs_without_prompt = processor(raw_image, return_tensors="pt")
        out = model.generate(**inputs_without_prompt)
        generated_text = processor.decode(out[0], skip_special_tokens=True)
        translation = GoogleTranslator(source='en', target='fr').translate(generated_text)
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
            "error": f"Erreur lors de la génération de la description: {e}"
        }
