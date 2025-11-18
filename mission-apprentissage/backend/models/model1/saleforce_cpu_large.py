#Running the model on CPU
import requests, time, sys, json, asyncio
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from deep_translator import GoogleTranslator
from utils.image_request import ImageRequest
from fastapi import FastAPI

app = FastAPI()

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

@app.get("/")
def root(): 
    return {"status": "salesforce_cpu_large model running"}

@app.post("/describe")
async def predict(request: ImageRequest):
    return await describe_with_salesforce_cpu_large(request.images)

async def process_image(image, processor, model):
    try :
        if image.startswith(('http://', 'https://')):
            raw_image = Image.open(requests.get(image, stream=True).raw).convert('RGB')
        else:
            raw_image = Image.open(image).convert('RGB')
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
            "error": f"Erreur lors de la génération de la description: {e}"
        }

async def describe_with_salesforce_cpu_large(images, output_file=None):
    tasks = [
        process_image(img, processor, model) for img in images
    ]
    imageList = await asyncio.gather(*tasks)
    return { "results": imageList }