import asyncio
from transformers import AutoProcessor, AutoModelForCausalLM
import requests, time
from PIL import Image
from deep_translator import GoogleTranslator
from fastapi import FastAPI
from utils.image_request import ImageRequest

app = FastAPI()

processor = AutoProcessor.from_pretrained("microsoft/git-large")
model = AutoModelForCausalLM.from_pretrained("microsoft/git-large")

@app.get("/")
def root():
    return {"status": "git_large model running"}

@app.post("/describe")
async def predict(request: ImageRequest):
    return await describe_image_with_git_large(request.images)

async def process_image(image, processor, model):
    try:
        if image.startswith(('http://', 'https://')):
            raw_image = Image.open(requests.get(image, stream=True).raw).convert('RGB')
        else:
            raw_image = Image.open(image).convert('RGB')
            
        start = time.time()
        pixel_values = processor(images=raw_image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values=pixel_values, max_length=50)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        translation = GoogleTranslator(source='auto', target='fr').translate(generated_text)
        end = time.time()
        
        return{
            "success": True,
            "english_description": generated_text,
            "french_description": translation,
            "generation_time": end - start
        }
        
    except Exception as e:
        return {
            "error": f"Erreur lors de l'ouverture de l'image : {e}"
        }
        
async def describe_image_with_git_large(image, output_file=None):
    tasks = [
        process_image(img, processor, model) for img in image
    ]
    imageList = await asyncio.gather(*tasks)            
    return { "results": imageList }
