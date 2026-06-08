import requests
from typing import Union
from fastapi import FastAPI, HTTPException
from ..models.image_request import ImageRequest

app = FastAPI()

@app.get("/")
def read_root():
    return {"API": "Success"}

@app.post("/predict")
async def describe_image(request: ImageRequest):
    """
    Point de terminaison pour décrire une image
    
    Args:
        request (ImageRequest): Requête contenant l'URL de l'image et l'option de traduction
        
    Returns:
        dict: Descriptions de l'image en anglais et français
    """
    try:
        # Validation de l'URL
        if not request.image or not isinstance(request.image, str):
            raise HTTPException(
                status_code=400, 
                detail="URL d'image invalide ou manquante"
            )
        # results = await describe_all_models(request.image)
        # return results

        #Appel modèle BLIP2
        try:
            blip2_url = "http://localhost:8001/describe"
            blip2_response = requests.post(blip2_url, json={"image": request.image})
            blip2_result = blip2_response.json()
        except Exception as e:
            blip2_result = {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Florence2 non disponible : {e}"
            }

        # Appel modèle Florence2
        try:
            florence_url = "http://localhost:8002/describe"
            florence_response = requests.post(florence_url, json={"image": request.image})
            florence_result = florence_response.json()
        except Exception as e:
            florence_result = {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Florence2 non disponible : {e}"
            }

        # Appel modèle GIT-large
        try:
            git_url = "http://localhost:8003/describe"
            git_response = requests.post(git_url, json={"image": request.image})
            git_result = git_response.json()
        except Exception as e:
            git_result = {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"GIT-large non disponible : {e}"
            }

        response_data = {
            "blip2_opt": {
                "success": blip2_result.get("success"),
                "english_description": blip2_result.get("english_description"),
                "french_description": blip2_result.get("french_description"),
                "error": blip2_result.get("error")
            },
            "florence2_large": {
                "success": florence_result.get("success"),
                "english_description": florence_result.get("english_description"),
                "french_description": florence_result.get("french_description"),
                "error": florence_result.get("error")
            },
            "git_large": {
                "success": git_result.get("success"),
                "english_description": git_result.get("english_description"),
                "french_description": git_result.get("french_description"),
                "error": git_result.get("error")
            }
        }
        return response_data

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de traitement: {str(e)}")
