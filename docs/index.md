# Documentation

## Présentation

**desc-image-ia** est une application qui génère automatiquement des descriptions textuelles pour les images contenues dans un fichier EPUB.

Un utilisateur dépose un EPUB via l'interface web ; le backend extrait les images du fichier et les envoie en parallèle à trois modèles d'IA de description d'image (BLIP, Florence-2, GIT Large). Les descriptions générées sont suivies en temps réel (progression par tâche) puis présentées à un humain, qui valide la description finale retenue pour chaque image.

L'application repose sur une architecture conteneurisée : une API FastAPI, un worker asynchrone (Taskiq/Redis) pour le traitement en arrière-plan, PostgreSQL pour la persistance, et une stack d'observabilité (Grafana LGTM) pour le suivi applicatif. Le détail est décrit dans [Architecture & Configuration du backend](CONFIG.md).

## Manuels

- [Manuel de déploiement](manuels/deploiement.md) — procédure complète de déploiement sur un VPS, du reverse proxy Nginx à HTTPS via Certbot.
- [Manuel d'utilisation](manuels/utilisation.md) — prise en main de l'application (compte, connexion, dépôt d'EPUB).

## Configuration

- [Architecture & Configuration du backend](CONFIG.md) — services docker-compose, rôles, ports exposés.
- [Configuration d'un serveur Ubuntu](CONFIG-SERVER.md) — installation Ubuntu, Nginx, Docker sur un VPS neuf.
- [Exemple de configuration Nginx](nginx/desc-image-ia.conf.example) — fichier prêt à copier sur le VPS (reverse proxy, upload EPUB volumineux, activation HTTPS avec Certbot).