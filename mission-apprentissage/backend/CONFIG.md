# Configuration du Backend 

## Prérequis 
- [pgAdmin](https://www.pgadmin.org/), pour accéder à la base de données PostgreSQL. Utilisez les informations de connexion suivantes :
- [Python >= 3.11](https://www.python.org/downloads/) doit petre installé sur votre ordinateur
- [pip](https://pypi.org/project/pip/), [uv](https://pypi.org/project/uv/) ou [poetry](https://python-poetry.org/) pour la gestion des dépendances et le lancement de l'api FastAPI
- [Bruno](https://www.usebruno.com/) ou [Postman](https://www.postman.com/) vous pouvez installer l'un des deux pour tester les requêtes API ou utiliser la documentation API Swagger UI 

**Accédez au migration gérées par Alembic**
```bash
    cd backend
```

**Appliquer les migrations existantes**
```bash
    alembic upgrade head
```

**Voir l'état actuel de la base**
```bash
    alembic current
```

**Créer une nouvelle migration après modifier un modèle**
```bash
    alembic revision --autogenerate -m "description du changement"
```

**Annuler la dernière migration**
```bash
alembic downgrade -1
```

**Lancement l'API FastAPI**
Sur votre terminal, faite la commande suivante:
```bash
    cd backend/ && fastapi dev 
    ou  
    uvicorn backend.api.api:app --reload --log-level debug
```

**Redis**
Dans le terminal faire la commande, pour accéder au serveur Redis :
```bash
    docker exec -it mission-apprentissage-redis-1 redis-cli
```

**Lancer les tests**
Dans le terminal, pour lancer les tests, faire la commande suivante :
```bash
    pytest -v backend/test
```

## Documentation de l'API
Une fois que l'API FastAPI est en cours d'exécution, vous pouvez accéder à la documentation interactive de l'API avec Swagger UI en ouvrant votre navigateur et en naviguant vers l'URL suivante :
```
    http://127.0.0.1:8000/docs
``` 

**Endpoints disponibles**
*Endpoints root*
- `GET /`
- `GET /health`

*Endpoints authentification*
- `POST /api/auth/register`
- `POST /api/auth/admin/register`
- `POST /api/auth/login`
- `GET /api/auth/users/me`
- `GET /api/auth/users/me/tasks`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`

*Endpoints pour l'upload Epub*

- `POST /api/epub/upload-epub/`
- `GET /api/epub/download-epub/{file_name}` 

*Endpoints gestion des descriptions*
- `GET /api/description/{task_id}`
- `POST /api/description/{task_id}/validate`
- `POST /api/description/add_descriptions`

*Endpoints gestion des tâches*
- `GET /api/task/admin`
- `GET /api/task/{task_id}`

## Tests

Commande pour lancer les tests unitaire, intégration et end to end.
```bash
    pytest -m unit /path/file_or_folder
    pytest -m integration /path/file_or_folder
    pytest -m e2e /path/file_or_folder
```

Commande pour lancer couvertures de tests.
```bash
    pytest -m unit --cov=. --cov-report=term-missing --cov-config=.coveragerc
    pytest -m integration --cov=. --cov-report=term-missing --cov-config=.coveragerc
    pytest -m e2e --cov=. --cov-report=term-missing --cov-config=.coveragerc
```