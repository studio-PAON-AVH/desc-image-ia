# Manuel de déploiement

## Objectif

Ce manuel décrit la procédure complète de déploiement du projet sur un serveur de production de type VPS, depuis la mise à disposition des images Docker jusqu'à la publication de l'application derrière un reverse proxy HTTPS. L'application repose sur plusieurs services spécialisés, seuls le backend FastAPI et Grafana LGTM ont un port sur 127.0.0.1, ils ne sont accessibles que via le serveur Nginx de l'hôte. Les autres services communiquent uniquement au sein du réseau Docker interne `app-net`.

## Architecture cible

L'architecture de déploiement côté production peut être résumée de la manière suivante :

- Internet → Nginx hôte sur les ports 80 et 443 (HTTP et HTTPS)
- Nginx redirige vers :
  - `127.0.0.1:8000` pour l'API backend
  - `127.0.0.1:3001` pour Grafana
- Le backend échange avec le worker, PostgreSQL et Redis
- Le worker appelle les services de modèles d'IA
- Le backend et le worker envoient leurs métriques et traces vers LGTM

## Prérequis

Le déploiement nécessite un serveur VPS Ubuntu ou Debian, avec systemd, Docker Engine 20.10+ et Docker Compose v2. Un utilisateur non-root appartenant au groupe `docker` est recommandé afin d'exécuter les commandes sans privilèges administratifs.

Le serveur doit également disposer de Nginx ou Apache configuré en reverse proxy, ainsi que le logiciel Certbot pour l'obtention et le renouvellement du certificat HTTPS. L'accès sortant vers `ghcr.io` est nécessaire pour télécharger les images conteneurisées.

Un pare-feu de type UFW doit autoriser uniquement les ports nécessaires pour les protocoles SSH, HTTP, HTTPS.

## Distribution des conteneurs

Les images Docker sont construites et publiées automatiquement par la chaîne d'intégration continue GitHub Actions sur GitHub Container Registry (GHCR). Aucun build n'est réalisé directement sur le VPS, le serveur se contente de récupérer les images publiées.

À chaque push, la CI exécute les contrôles de qualité du code. Chaque image est publiée avec deux tags : `latest`, utilisé en production, et un tag basé sur le git SHA, permettant de revenir facilement à une version antérieure en cas de rollback.

Le mode de développement local reste disponible à partir du dépôt source, via la commande `docker compose up -d --build` pour effectuer différents tests avant de push les modifications.

## Déploiement serveur

Les commandes de déploiement sont exécutées depuis le répertoire de production copié sur le VPS. Le fichier d'environnement utilisé par Docker Compose est `.env`. Le déploiement automatisé est pris en charge par le workflow GitHub Actions précédemment mentionné dans la Partie 4 – Protocole de déploiement continu. Après le premier déploiement, et à chaque évolution du schéma de base de données, les migrations Alembic doivent être appliquées afin de garantir la cohérence du modèle de données.

Le reverse proxy Nginx doit ensuite être configuré pour router les requêtes vers les bons services :

- L'endpoint `/` vers l'interface frontend distribuée par le backend
- L'endpoint `/api/` vers le backend
- L'endpoint `/grafana/` vers la pile d'observabilité

La configuration Nginx doit également inclure `client_max_body_size 500M`, indispensable pour l'envoi de fichiers EPUB volumineux. Une fois le DNS correctement configuré, Certbot permet d'activer HTTPS automatiquement.

## Vérifications après déploiement

Après la mise en service, il convient de vérifier :

- La bonne récupération des images Docker depuis GHCR,
- La création et l'état des conteneurs Docker,
- Le bon fonctionnement des services,
- La communication entre frontend et backend,
- L'exécution correcte des migrations,
- L'accès à Grafana,
- Les journaux applicatifs,
- Ainsi que le bon déroulement du traitement avec un scénario complet :
  - Création de compte / connexion,
  - Dépôt d'un EPUB,
  - Traitement des images,
  - Génération des descriptions,
  - Validation des descriptions et téléchargement du fichier enrichi

## Diagnostic rapide

Les incidents les plus fréquents concernent :

- Un backend non opérationnel, souvent lié à une configuration PostgreSQL, à des migrations incomplètes ou à la configuration des politiques CORS.
- Une erreur 502 (Bad Gateway), généralement causée par un conteneur arrêté ou un mauvais réglage du proxy.
- Une surcharge mémoire des modèles, qui peut nécessiter un ajustement des paramètres d'exécution.
- Un refus d'accès à GHCR, résolu par une nouvelle authentification.
