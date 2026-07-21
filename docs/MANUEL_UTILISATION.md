# Manuel d'utilisation

## Accéder à l'application

Ouvrir l'adresse suivante dans un navigateur web : `https://votrenomdedomaine.com`, l'interface s'affiche immédiatement. Aucun plugin ou installation supplémentaire n'est requis.

### Créer un compte et se connecter

#### Inscription
Depuis la page de connexion :

- Cliquer sur « S'inscrire »
- Renseigner les informations suivantes :
  - Nom utilisateur,
  - Adresse e-mail,
  - Mot de passe (minimum 8 caractères)
- Valider le formulaire

L'utilisateur est automatiquement redirigé vers son tableau de bord. Si l'adresse e-mail est déjà utilisée, le système renvoie une erreur HTTP 409 (Conflict), avec un message personnalisé pour signaler le problème.

Les comptes administrateur ne peuvent pas être créés via le formulaire public, ils sont générés manuellement par un administrateur existant.

#### Connexion
Pour se connecter :
- Saisir l'adresse e-mail et le mot de passe,
- Cliquer sur « Se connecter »

La session est gérée via un cookie sécurisé contenant un JWT.

### Tableau de bord
Le tableau de bord affiche la liste des tâches associées au compte utilisateur. Chaque upload d'EPUB correspond à une tâche distincte.

| Colonne | Description |
| --- | --- |
| Fichier | Nom du fichier EPUB |
| Statut | En attente, En cours, Terminé, Échoué |
| Progression | Nombre d'images traitées sur le total |
| Date | Date de création de la tâche |
| Actions | Voir le statut ou ouvrir les descriptions |

Le bouton « Nouvel upload », situé en haut à droite, permet d'ajouter un nouveau fichier EPUB.

### Uploader un EPUB
Pour uploader un fichier :

- Cliquer sur « Upload » ou « Nouvel upload »
- Sélectionner un fichier au format `.epub` (unique format accepté, taille maximale 500 Mo).
- Cliquer sur « Uploader ». Une barre de progression indique l'avancement du transfert.
- Une fois l'upload terminé, l'utilisateur est redirigé vers la page « Statut de la tâche ».

Erreurs possibles : 413 (fichier trop volumineux), 415 (format non supporté), 422 (EPUB invalide).

### Suivre le traitement
Le statut de la tâche évolue automatiquement selon le cycle suivant : en attente, puis en cours, enfin terminé ou échoué. La progression indique le nombre d'images déjà traitées. En arrière-plan, le worker envoie chaque image aux trois modèles d'IA :

- Salesforce BLIP,
- Florence-2,
- GIT Large.

Chaque modèle génère une description, ensuite traduite en français. Les descriptions apparaissent au fil du temps, mais la validation finale n'est possible qu'une fois la tâche « Terminée ». En cas d'échec, un bouton « Réessayer » permet de relancer le traitement.

### Validation des descriptions
Pour chaque image, trois propositions de description sont affichées, une par modèle d'IA. La validation se déroule comme suit :

- Cliquer sur la proposition la plus pertinente. La sélection est mise en surbrillance avec l'indication « sélectionné ». Recliquer désélectionne la proposition.
- L'utilisateur peut modifier la proposition sélectionnée ou écrire une description personnalisée, sans obligation de sélectionner une description générée par l'un des modèles IA.

Chaque image doit disposer d'une description ; sans description, la validation finale est bloquée.

### Télécharger l'EPUB enrichi

Une fois toutes les descriptions validées :

- Cliquer sur « Valider tout et télécharger ».
- Les descriptions sont enregistrées en base de données et injectées dans l'EPUB, via l'attribut `alt` des images dans les métadonnées.
- Un fichier est téléchargé automatiquement, puis l'utilisateur est redirigé vers le tableau de bord.
