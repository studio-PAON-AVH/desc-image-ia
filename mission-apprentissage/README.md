# Guide pour récupérer le projet sur votre ordinateur

## Prérequis 
- [Git](https://git-scm.com/) doit être installé sur votre ordinateur
- [Python](https://www.python.org/downloads/) doit petre installé sur votre ordinateur
- [Docker](https://www.docker.com/) doit être installé sur votre ordinateur

uvicorn backend.api.api:app --reload --log-level debug

## Étapes à suivre

1. **Ouvrez votre terminal** 

2. **Choisissez le dossier où vous souhiatez cloner le projet**

3. **Clonez le dépôt**
    Remplacez '<URL_DU_DE¨POT>' par l'url du dépôt Git du projet:
    ```bash
        git clone <URL_DU_DEPOT>
    ```

4. **Accédez au dossier du projet**
    ```bash
        cd mission-apprentissage
    ```

5. **Créez un environnement virtuel**
    ```bash
        python -m venv venv
    ```

6. **Installez des dépendances**
    Si le projet utilise Python et un fichier `requirements.txt` :
    ```bash 
        pip install -r requirements.txt
    ```

7. **Créez les images et les containeurs Docker 
    ```bash
        docker-compose up --build -d
    ```

8. **Tester les requêtes API**
    Sur votre terminal, lancer l'api FastAPI:
    ```bash
        cd backend/api, fastapi dev 
        ou  
        uvicorn backend.api.api:app --reload --log-level debug

    ```
    [Bruno](https://www.usebruno.com/) ou [Postman](https://www.postman.com/) vous pouvez installer l'un des deux pour tester les requêtes API ou utiliser la documentation API Swagger UI 

9. **Requête API**

    ### Exemple de body pour la requête POST (Génération de description)
    ***Route***
    ```
    POST http://127.0.0.1:8000/predict
    ```
    ***Body***
    ```json 
        {
            "images": [
                "<CHEMIN_DE_L_IMAGE_LOCAL>"
            ]
        }
    ```

    ***Route***
    ```
    GET http://127.0.0.1:8000/predict/task_id
    ```

    ### Exemple de body pour la requête POST (Classification des images)*
    ***Route***
    ```
    POST http://127.0.0.1:8000/classify
    ```
    ***Body***
    ```json
        {
            "images": [
                "https://www.votretourdumonde.com/wp-content/uploads/2013/06/magnifique-paysage.jpg"
            ]
        }
    ```