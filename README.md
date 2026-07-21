# Guide pour récupérer le projet sur votre ordinateur

## Prérequis 
- [pgAdmin](https://www.pgadmin.org/), pour accéder à la base de données PostgreSQL. Utilisez les informations de connexion suivantes :
- [Python >= 3.11](https://www.python.org/downloads/) doit être installé sur votre ordinateur
- [Poetry](https://python-poetry.org/) pour la gestion des dépendances et le lancement de l'api FastAPI
- [Docker](https://www.docker.com/) doit être installé sur votre ordinateur


## Étapes à suivre
1. **Ouvrir un terminal** 

2. **Clonez le dépôt**
    Remplacez '<URL_DU_DEPOT>' par l'url du dépôt Git du projet:
    ```bash
        git clone <URL_DU_DEPOT>
    ```

3. **Accédez au dossier du projet**
    ```bash
        cd desc-image-ia
    ```

4. **Créez un environnement virtuel**
    ```bash
        python -m venv venv
    ```

5. **Installez les dépendances**
    Placez-vous dans le dossier `backend` (qui contient le fichier `pyproject.toml` et `poetry.lock`), puis installez les dépendances avec Poetry :
    ```bash
        cd backend
        poetry install
    ```

6. **Créez les images et les containeurs Docker**
    ```bash
        docker-compose up --build -d
    ```

## Documentation

- [Manuel de déploiement](docs/MANUEL_DEPLOIEMENT.md) — procédure de mise en production sur un VPS
- [Manuel d'utilisation](docs/MANUEL_UTILISATION.md) — prise en main de l'application par les utilisateurs
- [Configuration](docs/CONFIG.md) — variables d'environnement de l'application
- [Configuration serveur](docs/CONFIG-SERVER.md) — configuration du serveur (reverse proxy, etc.)


