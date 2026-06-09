import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


@csrf_exempt
def process_describe_image(request):
    """Proxy l'upload EPUB vers FastAPI"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return JsonResponse({'error': 'Authentification requise'}, status=401)

    epub_file = request.FILES.get('epub')
    if not epub_file:
        return JsonResponse({'error': 'Aucun fichier EPUB fourni'}, status=400)

    try:
        response = requests.post(
            f"{settings.FASTAPI_URL}/api/epub/upload-epub/",
            files={'upload': (epub_file.name, epub_file.read(), epub_file.content_type)},
            headers={'Authorization': auth_header},
            timeout=120,
        )

        data = response.json()

        if response.status_code == 201:
            return JsonResponse({'success': True, 'results': data}, status=200)
        else:
            return JsonResponse(
                {'error': data.get('detail', 'Erreur lors du traitement')},
                status=response.status_code,
            )

    except requests.Timeout:
        return JsonResponse(
            {'error': 'Le traitement a pris trop de temps'},
            status=408,
        )
    except requests.ConnectionError:
        return JsonResponse(
            {'error': 'Impossible de se connecter au serveur FastAPI'},
            status=502,
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Erreur inattendue: {str(e)}'},
            status=500,
        )