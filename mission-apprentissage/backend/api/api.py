from fastapi import FastAPI, HTTPException
from ..models.image_request import ImageRequest
from ..models.image_describe import get_image_describe
app = FastAPI()

@app.get("/")
def read_root():
    return {"API": "Success"}

@app.post("/predict")
def describe_image(request: ImageRequest):
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

        results = get_image_describe(request.image)
        return results  

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de traitement: {str(e)}")
