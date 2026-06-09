import json, requests, os, time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib import messages
from urllib.parse import urlparse

def home_view(request):
    """Vue d'accueil avec formulaire d'upload d'image"""
    return render(request, 'home.html')

def process_view(request):
    return render(request, 'process.html', {
        'fastapi_url': settings.FASTAPI_URL
    })

def review_view(request):
    task_id = request.GET.get('task_id', '')
    return render(request, 'review.html', {'task_id': task_id, 'fastapi_url': settings.FASTAPI_URL})

def login_view(request):
    return render(request, 'login.html', {
        'next_url': request.GET.get('next', '/process/'),
        'fastapi_url': settings.FASTAPI_URL
    })

def register_view(request):
    return render(request, 'register.html', {
        'fastapi_url': settings.FASTAPI_URL
    })

