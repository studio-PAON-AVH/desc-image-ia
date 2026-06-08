import torch
from transformers import CLIPProcessor, CLIPModel
# from transformers.image_utils import load_image

def classify_image(images):
    """
    Classifie une ou plusieurs images à l'aide du modèle CLIP.
    Args:
        images (list ou str): Liste d'URL/images ou une seule image.
    Returns:
        list: Liste des labels prédits pour chaque image.
    """
    if isinstance(images, str):
        images = [images]

    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    labels = ["pie chart", "cartoon", "painting", "animal", "paysage", "chart", "people"]

    results = []
    for image in images:
        inputs = processor(
            text=labels,
            images=image,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)

        best_label_idx = probs.argmax().item()
        best_label = labels[best_label_idx]
        
        results.append({
            "image": image,
            "label": best_label,
            "probability": float(probs[0, best_label_idx])
        })

    return results