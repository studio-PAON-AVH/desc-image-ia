import requests

def get_image_describe(images):
    def call(url, image):
        try: 
            response = requests.post(url, json={"image": image})
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "english_description": None,
                "french_description": None,
                "error": f"Erreur lors de l'appel au service {url}: {e}"
            }
    # return {
    #     "salesforce_cpu_large": call("http://localhost:8001/describe"),
    #     "florence2_large": call("http://localhost:8002/describe"),
    #     "git_large": call("http://localhost:8003/describe")
    # }
    
    results = []
    for image in images:
        results.append({ 
            "image": image,
            "salesforce_cpu_large": call("http://localhost:8001/describe", image),
            "florence2_large": call("http://localhost:8002/describe", image),
            "git_large": call("http://localhost:8003/describe", image)
        })
        
    return results