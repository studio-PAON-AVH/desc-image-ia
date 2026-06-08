import json, requests, os, tempfile
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib import messages
from urllib.parse import urlparse

def index(request):
    """Vue d'accueil avec formulaire d'upload d'image"""
    return render(request, 'home.html')

def home_view(request):
    """Vue d'accueil avec formulaire d'upload d'image"""
    return render(request, 'home.html')

@csrf_exempt
def process_image_view(request):
    """Vue pour traiter l'image et appeler l'API FastAPI"""
    if request.method != 'POST':
        return redirect('home')
    
    try:
        image_urls = []
        translate_to_french = request.POST.get('translate_to_french', False) == 'on'
        
        # Traitement de l'URL d'image
        image_url = request.POST.get('image_url', '').strip()
        if image_url:
            # Validation basique de l'URL
            parsed_url = urlparse(image_url)
            if parsed_url.scheme in ['http', 'https']:
                image_urls.append(image_url)
            else:
                messages.error(request, "URL d'image invalide")
                return redirect('home')
        
        # Traitement du fichier uploadé
        if 'image_file' in request.FILES:
            uploaded_file = request.FILES['image_file']
            
            # Validation du type de fichier
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                messages.error(request, "Type de fichier non supporté. Utilisez JPG, PNG, GIF, BMP ou WEBP.")
                return redirect('home')
            
            # Sauvegarder le fichier temporairement
            file_path = default_storage.save(
                f'temp/{uploaded_file.name}',
                ContentFile(uploaded_file.read())
            )
            
            # Créer l'URL complète pour le fichier
            full_file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)
            image_urls.append(full_file_url)
        
        if not image_urls:
            messages.error(request, "Veuillez fournir une URL d'image ou uploader un fichier.")
            return redirect('home')
        
        # Appel à l'API FastAPI pour la description
        api_url = "http://localhost:8000"  # URL de votre API FastAPI
        
        # Préparer les données pour l'API
        api_data = {
            "images": image_urls,
            "translate_to_french": translate_to_french
        }
        
        # Appel à l'endpoint de description
        try:
            description_response = requests.post(
                f"{api_url}/predict",
                json=api_data,
                timeout=30
            )
            description_response.raise_for_status()
            description_data = description_response.json()
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Erreur lors de l'appel à l'API de description: {str(e)}")
            return redirect('home')
        
        # Appel à l'endpoint de classification
        try:
            classification_response = requests.post(
                f"{api_url}/classify",
                json=api_data,
                timeout=30
            )
            classification_response.raise_for_status()
            classification_data = classification_response.json()
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Erreur lors de l'appel à l'API de classification: {str(e)}")
            return redirect('home')
        
        # Préparer les données pour le template
        results = {
            'image_urls': image_urls,
            'descriptions': description_data.get('description', []),
            'classifications': classification_data.get('classification', []),
            'translate_to_french': translate_to_french
        }
        
        # Stocker les résultats en session pour la vue de résultats
        request.session['results'] = results
        
        return redirect('results')
        
    except Exception as e:
        messages.error(request, f"Erreur lors du traitement de l'image: {str(e)}")
        return redirect('home')

def results_view(request):
    """Vue pour afficher les résultats de l'analyse d'image"""
    results = request.session.get('results')
    
    if not results:
        messages.error(request, "Aucun résultat trouvé. Veuillez d'abord analyser une image.")
        return redirect('home')
    
    return render(request, 'results.html', {'results': results})

def clear_results(request):
    """Vue pour effacer les résultats de la session"""
    if 'results' in request.session:
        del request.session['results']
    return redirect('home')

@csrf_exempt
def api_process_image(request):
    """API endpoint JSON pour traiter une image (pour les appels AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        data = json.loads(request.body)
        image_urls = data.get('images', [])
        translate_to_french = data.get('translate_to_french', False)
        
        if not image_urls:
            return JsonResponse({'error': 'Aucune image fournie'}, status=400)
        
        # Appel à l'API FastAPI
        api_url = "http://localhost:8000"
        api_data = {
            "images": image_urls,
            "translate_to_french": translate_to_french
        }
        
        # Description
        description_response = requests.post(f"{api_url}/predict", json=api_data, timeout=30)
        description_response.raise_for_status()
        description_data = description_response.json()
        
        # Classification
        classification_response = requests.post(f"{api_url}/classify", json=api_data, timeout=30)
        classification_response.raise_for_status()
        classification_data = classification_response.json()
        
        return JsonResponse({
            'success': True,
            'descriptions': description_data.get('description', []),
            'classifications': classification_data.get('classification', [])
        })
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Erreur API: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Erreur: {str(e)}'}, status=500)
