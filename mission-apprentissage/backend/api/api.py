from fastapi import FastAPI, HTTPException
from ..models.image_request import ImageRequest
from ..models.image_describe import get_image_describe
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
        # Faire la classificication de l'image, la récupérer puis envoyer l'image à décrire
        r = await get_image_describe(request.images)
        return {"descriptions": r}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de traitement: {str(e)}")
