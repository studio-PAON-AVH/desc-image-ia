import json, requests, os, time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib import messages
from urllib.parse import urlparse

# URL de votre API FastAPI
FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://localhost:8000')

def home_view(request):
    """Vue d'accueil avec formulaire d'upload d'image"""
    return render(request, 'home.html')

@csrf_exempt
def api_process_image(request):
    """API endpoint pour traiter plusieurs images (retour JSON)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Aucune image fournie'}, status=400)
    
    try:
        # Récupérer toutes les images envoyées
        image_files = request.FILES.getlist('image')
        
        if not image_files:
            return JsonResponse({'error': 'Aucune image fournie'}, status=400)
        
        # Sauvegarder temporairement toutes les images
        image_paths = []
        for image_file in image_files:
            file_path = default_storage.save(f'temp/{image_file.name}', ContentFile(image_file.read()))
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            image_paths.append(full_path)
        
        # Envoyer à l'API FastAPI pour description (toutes les images)
        payload = {'images': image_paths}
        response = requests.post(f'{FASTAPI_URL}/predict', json=payload)
        
        if response.status_code == 201:
            task_id = response.json().get('task_id')
            
            # Attendre un peu et vérifier le résultat
            max_attempts = 120  # 2 minutes max (120 secondes)
            wait_time = 1  # Attendre 1 seconde entre chaque vérification
            
            for attempt in range(max_attempts):
                time.sleep(wait_time)
                
                try:
                    result_response = requests.get(f'{FASTAPI_URL}/predict/{task_id}', timeout=10)
                    
                    if result_response.status_code == 200:
                        results = result_response.json().get('result', {})
                        
                        # Nettoyer les fichiers temporaires
                        for img_path in image_paths:
                            if os.path.exists(img_path):
                                try:
                                    os.remove(img_path)
                                except:
                                    pass
                        
                        return JsonResponse({
                            'success': True,
                            'results': results,
                            'task_id': task_id,
                            'images_count': len(image_paths)
                        })
                    elif result_response.status_code == 202:
                        # Toujours en cours, continuer d'attendre
                        continue
                    else:
                        # Erreur
                        return JsonResponse({
                            'error': f'Erreur API (statut {result_response.status_code})',
                            'task_id': task_id
                        }, status=result_response.status_code)
                        
                except requests.exceptions.Timeout:
                    continue
                except Exception as e:
                    continue
            
            # Si pas de résultat après max_attempts
            return JsonResponse({
                'error': 'Le traitement prend plus de temps que prévu. Veuillez réessayer dans quelques instants.',
                'task_id': task_id
            }, status=408)
        
        else:
            return JsonResponse({'error': 'Erreur lors de l\'envoi à l\'API'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

