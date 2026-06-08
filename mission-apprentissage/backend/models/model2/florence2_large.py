import torch, requests, time
from fastapi import FastAPI
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM 
from deep_translator import GoogleTranslator
from backend.utils.image_request import ImageRequest

app = FastAPI()

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", torch_dtype=torch_dtype, trust_remote_code=True).to(device)
processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)

@app.get("/")
def root(): 
    return {"status": "florence2_large model running"}

@app.post("/describe")
def predict(request: ImageRequest):
    return describe_image_with_florance2_large(request.image)

def describe_image_with_florance2_large(image, output_file=None):
    # si le lien de l'image comment par http ou https, on ouvre l'image, 
    # sinon il s'agit d'une image locale
    if image.startswith(('http://', 'https://')):
        try:
            raw_image = Image.open(requests.get(image, stream=True).raw).convert('RGB')
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors de l'ouverture de l'image : {e}"
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
        start = time.time()
        task = "<MORE_DETAILED_CAPTION>"

        inputs = processor(text=task, images=raw_image, return_tensors="pt").to(device, torch_dtype)

        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
            do_sample=False
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]

        parsed_answer = processor.post_process_generation(generated_text, task=task, image_size=(raw_image.width, raw_image.height))
        #translation = Translator(to_lang="fr").translate(parsed_answer[task])
        translated = GoogleTranslator(source='auto', target='fr').translate(parsed_answer[task])
        end = time.time()
        return {
            "success": True,
            "english_description": parsed_answer[task],
            "french_description": translated,
            "generation_time": end - start
        }

    except Exception as e:
        return {
            "success": False,
            "english_description": None,
            "french_description": None,
            "error": f"Model error: {e}"
        }