# Guide pour récupérer le projet sur votre ordinateur

## Prérequis 
- [pgAdmin](https://www.pgadmin.org/), pour accéder à la base de données PostgreSQL. Utilisez les informations de connexion suivantes :
- [Python >= 3.11](https://www.python.org/downloads/) doit petre installé sur votre ordinateur
- [pip](https://pypi.org/project/pip/), [uv](https://pypi.org/project/uv/) ou [poetry](https://python-poetry.org/) pour la gestion des dépendances et le lancement de l'api FastAPI
- [Docker](https://www.docker.com/) doit être installé sur votre ordinateur


## Étapes à suivre
1. **Ouvrir un terminal** 

2. **Clonez le dépôt**
    Remplacez '<URL_DU_DE¨POT>' par l'url du dépôt Git du projet:
    ```bash
        git clone <URL_DU_DEPOT>
    ```

3. **Accédez au dossier du projet**
    ```bash
        cd mission-apprentissage
    ```

4. **Créez un environnement virtuel**
    ```bash
        python -m venv venv
    ```

5. **Installez des dépendances**
    Si le projet utilise Python et un fichier `requirements.txt` :
    ```bash 
        pip install -r requirements.txt
    ```

6. **Créez les images et les containeurs Docker**
    ```bash
        docker-compose up --build -d
    ```


