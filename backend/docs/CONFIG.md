# Architecture & Configuration du Backend

Ce document explique **comment le backend est structuré** et **comment les pièces communiquent**, puis donne les commandes de configuration et d'exploitation.

---

## 1. Les services (docker-compose)

| Service | Rôle | Exposé |
|---|---|---|
| **backend** (`fastapi`) | API HTTP : auth, upload EPUB, lecture des résultats. Distribue également le frontend. | `8000` |
| **worker** (`worker-taskiq`) | Consomme la file Redis et exécute le traitement EPUB → IA → DB. | — (interne) |
| **postgres** | Base de données relationnelle. | `5432` |
| **redis** | Double rôle : **file de tâches** taskiq + **stockage de l'état/progression** de chaque tâche (`task_id`). | `6379` |
| **model-blip / model-florence / model-git** | 3 services d'inférence IA, chacun expose `POST /describe`. | `8000` interne |
| **lgtm** | Stack d'observabilité (Loki, Grafana, Tempo, Mimir) recevant l'OTLP. | `3001` (Grafana) |

> Trois fichiers compose coexistent : `docker-compose.yml` (local), `docker-compose.dev.yml` et `docker-compose.prod.yml` (images pré-construites depuis GHCR).

---

## 3. Le flux complet d'une requête

**Upload** — `POST /api/epub/upload-epub` (`epub/controller.py`)
1. Validation : extension `.epub`, taille ≤ 100 Mo, magic bytes `PK\x03\x04`, non-doublon.
2. L'EPUB est écrit dans un fichier temporaire (`UPLOAD_TEMP_DIR`, partagé via le volume `epub_shared`).
3. Création d'un `task_id` (UUID) → état initial stocké dans **Redis**.
4. Création des lignes `Task` + `Epub` en **PostgreSQL**.
5. La tâche est **enfilée** dans le worker : `process_epub_describe.kiq(...)`.
6. Réponse immédiate : `{ "task_id": "..." }`.

**Traitement** — `worker/worker.py : process_epub_describe`
1. `Task` passe à `in_progress`.
2. `extract_images_epub` extrait les images de l'EPUB (dossier temporaire).
3. `save_images` insère les lignes `Images` en DB ; les images sont encodées en base64.
4. `stream_image_describe` envoie les images aux **3 modèles en parallèle**, par batch, et *yield* chaque résultat dès qu'il revient (un sémaphore par modèle plafonne la concurrence).
5. Chaque slice (batch × modèle) est **persisté** (`DescriptionByIA`) et l'état Redis est mis à jour → progression en temps réel.
6. En fin : `Task` → `completed`, état final écrit dans Redis, dossier temporaire nettoyé.
7. Robustesse : `retry_on_error` (3 essais) ; au démarrage du worker, `recover_stuck_tasks` reprend les tâches restées `in_progress`.

**Suivi & résultats**
- `GET /api/task/{task_id}` / `GET /api/description/{task_id}` : le frontend interroge l'état (servi depuis Redis / DB).
- `POST /api/description/{task_id}/validate` : un humain valide une description → `DescriptionFinale`.

---

## 4. Modèle de données (`core/database/config.py`)

SQLAlchemy **async** (`asyncpg`), migrations via **Alembic**.

```
User ─┬─< Task ─┬─< Epub ─┬─< Images ─┬─< DescriptionByIA   >─ ModelsIA
      │         │         │           └─< DescriptionFinale >─ ModelsIA
      └─< RefreshToken    └────────────── (Images relié à Task et Epub)
```

- **User / RefreshToken** : authentification (JWT + refresh tokens), rôles `user`/`admin`.
- **Task** : une exécution (`task_id_redis`, `status`, `total_images`, `processed_images`).
- **Epub** : le fichier uploadé rattaché à une `Task`.
- **Images** : une image extraite (`image_file_name`, `image_position_in_epub`).
- **DescriptionByIA** : description brute produite par un modèle pour une image.
- **DescriptionFinale** : description retenue/validée par un humain.
- **ModelsIA** : référentiel des modèles (BLIP, Florence-2, GIT Large).

---

## 5. Configuration (variables d'environnement)

Les réglages sont centralisés dans `core/settings.py` (Pydantic `Settings`). Le fichier `.env` chargé est déterminé par `APP_ENV`.

⚠️ **Deux mécanismes distincts dans compose, à ne pas confondre :**
- **`${VAR}`** (interpolation) : résolu par Compose **au parsing**, en lisant le `.env` du dossier (ou `--env-file`). Sert p. ex. au healthcheck `pg_isready -U ${POSTGRES_USER}`.
- **`env_file:` / `environment:`** : injecté **dans le conteneur** au runtime.

Variables clés : `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `POSTGRES_{HOST,USER,PASSWORD,DB,SSL}`, `REDIS_{HOST,PORT,URL}`, `UPLOAD_TEMP_DIR`, `URL_SALESFORCE_CPU_LARGE` / `URL_FLORANCE_2_LARGE` / `URL_GIT_LARGE`, `BATCH_SIZE`, `BATCH_MAX`, `DEBUG`.

> 🩺 **Piège connu** : si `POSTGRES_USER`/`POSTGRES_PASSWORD` sont **vides** dans le `.env`, le healthcheck devient `pg_isready -U -d` → conteneur **unhealthy** → `backend`/`worker` refusent de démarrer (`dependency failed to start`). Les identifiants Postgres ne sont par ailleurs lus **qu'à la première initialisation** du volume `postgres_data`.

---

## Prérequis (développement local)
- [pgAdmin](https://www.pgadmin.org/) pour accéder à PostgreSQL.
- [Python >= 3.11](https://www.python.org/downloads/).
- [pip](https://pypi.org/project/pip/), [uv](https://pypi.org/project/uv/) ou [poetry](https://python-poetry.org/) pour les dépendances et le lancement de l'API.
- [Bruno](https://www.usebruno.com/) ou [Postman](https://www.postman.com/) pour tester l'API (ou Swagger UI).

## Migrations (Alembic)
```bash
cd backend
alembic upgrade head                                   # appliquer les migrations
alembic current                                        # état actuel
alembic revision --autogenerate -m "description"       # nouvelle migration après modif d'un modèle
alembic downgrade -1                                   # annuler la dernière
```

## Lancer l'API
```bash
cd backend/ && fastapi dev
# ou
uvicorn backend.api.api:app --reload --log-level debug
```

## Redis (CLI)
```bash
docker exec -it desc-image-ia-redis-1 redis-cli
```

## Documentation interactive (Swagger UI)
```
http://127.0.0.1:8000/docs
```

### Endpoints
*Root* — `GET /` · `GET /health`

*Authentification* — `POST /api/auth/register` · `POST /api/auth/admin/register` · `POST /api/auth/login` · `GET /api/auth/users/me` · `GET /api/auth/users/me/tasks` · `POST /api/auth/refresh` · `POST /api/auth/logout`

*Upload EPUB* — `POST /api/epub/upload-epub` · `GET /api/epub/download-epub/{file_name}`

*Descriptions* — `GET /api/description/{task_id}` · `POST /api/description/{task_id}/validate` · `POST /api/description/add_descriptions`

*Tâches* — `GET /api/task/admin` · `GET /api/task/{task_id}`

## Tests
```bash
pytest -m unit /path/file_or_folder
pytest -m integration /path/file_or_folder
pytest -m e2e /path/file_or_folder
```

Avec couverture :
```bash
pytest -m unit --cov=. --cov-report=term-missing --cov-config=.coveragerc
pytest -m integration --cov=. --cov-report=term-missing --cov-config=.coveragerc
pytest -m e2e --cov=. --cov-report=term-missing --cov-config=.coveragerc
```
