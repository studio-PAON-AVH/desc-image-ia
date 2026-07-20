# CHANGELOG

## [1.0.0](https://github.com/studio-PAON-AVH/desc-image-ia/releases/tag/1.0.0) - 2026-07-20 09:55:08+00:00

Première version d'un prototype fonctionnelle d'un logiciel web pour la génération de description d'images à partir de fichiers EPUB.

## Fonctionnalités

* Nettoyage du code  by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/1
* Intégration du pipeline CI/CD et OpenTelemetry by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/3
* Suppression du code mort by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/4
* docs: documentations de configuration serveur by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/6
* Gestion du stockage des images by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/7
* Intégration de MinIO pour le stockage des images by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/8
* Correction de l'ajout des descriptions by @Yuta1409 in https://github.com/studio-PAON-AVH/desc-image-ia/pull/12

**Full Changelog**: https://github.com/studio-PAON-AVH/desc-image-ia/commits/1.0.0

### Feature

- general:
  - ajout du service MinIO dans `docker-compose.prod.yml` ([25d3659](https://github.com/studio-PAON-AVH/desc-image-ia/commit/25d365963c04b53e873895a38bd24d8eda596ae3))
  - ajout de la configuration MinIO ([b4b9007](https://github.com/studio-PAON-AVH/desc-image-ia/commit/b4b900720177e6055105b75923fff47ac2e784a6)) ([#13](https://github.com/studio-PAON-AVH/desc-image-ia/pull/13))
  - implementation annulation pour une tache ([a4f51ac](https://github.com/studio-PAON-AVH/desc-image-ia/commit/a4f51acc5e2daa1431df897eeb818778f9e1c1fb)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - ajout dockerfile pour minio ([388cfac](https://github.com/studio-PAON-AVH/desc-image-ia/commit/388cfac476967110cc35d66469346415ae0e76b6)) ([#8](https://github.com/studio-PAON-AVH/desc-image-ia/pull/8))
  - workflow deploiement pour le developpement ([a1fe9d4](https://github.com/studio-PAON-AVH/desc-image-ia/commit/a1fe9d48b9eb712175b3acb523dac9f9221c9036)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - integration opentelemetry
- Ajout des métriques métier, l'upload, tâches, durées, file d'attente des modèles IA
- Auto-instrumentation avec OpenTelemetry pour FastAPI, SQLAlchemy, Redis, et httpx
- Stack Grafana LGTM dans une image Docker dans , avec 4 tableau de bord provisionnés
- Tracing distribué entre les appelles API et worker via middleware taskiq
- Logs rédirigés vers Loki
- Suppression de l'image frontend-react, distribution du front par le backend via ([692983c](https://github.com/studio-PAON-AVH/desc-image-ia/commit/692983cb466a854538e3856238a82d9af95f6140)) ([#1](https://github.com/studio-PAON-AVH/desc-image-ia/pull/1))
  - pipeline CI/CD et distribution frontend par le backend FastAPI ([f11dd1c](https://github.com/studio-PAON-AVH/desc-image-ia/commit/f11dd1cb4d64b893614d02f9d43fe7fadd3539ce)) ([#1](https://github.com/studio-PAON-AVH/desc-image-ia/pull/1))
  - configuration SSL ([74a7ae2](https://github.com/studio-PAON-AVH/desc-image-ia/commit/74a7ae212f43f5525c71067945acf3ac3e5b65ae))
  - configuration frontend ([4000d98](https://github.com/studio-PAON-AVH/desc-image-ia/commit/4000d98717fdedb1cd77e40e8f0d62a10933bf5e))
  - ajout des composants UI ([0316cf1](https://github.com/studio-PAON-AVH/desc-image-ia/commit/0316cf1d6cb25838e6a9e50de4c27d229cd85746))
  - communication api ([5118937](https://github.com/studio-PAON-AVH/desc-image-ia/commit/5118937159bb0075c65dd49cd6b111512a59b846))
  - migration vers react ([626b150](https://github.com/studio-PAON-AVH/desc-image-ia/commit/626b15024012247b2ed3002c5c18b7a64a86ccf4))
  - pipelines CI/CD ([7c9275b](https://github.com/studio-PAON-AVH/desc-image-ia/commit/7c9275b1a234e646959749794bbaed126b01a91c))
  - couverture de tests ([e115a87](https://github.com/studio-PAON-AVH/desc-image-ia/commit/e115a8786729487e1815afd4db38782d388310c9))
  - mise à jour des tests ([eea9358](https://github.com/studio-PAON-AVH/desc-image-ia/commit/eea9358df42f99feb2522f38d1b0c751065148d8))
  - tableau de révision des descriptions ([0447326](https://github.com/studio-PAON-AVH/desc-image-ia/commit/044732651551c96723ddf5544e33734b2de05664))
  - formulaire d'authentification ([4566200](https://github.com/studio-PAON-AVH/desc-image-ia/commit/45662008890d1b965b2b3273dd3e1ccdb2431fb7))
  - fonctionnalité d'ajout descriptions dans EPUB ([f9373c6](https://github.com/studio-PAON-AVH/desc-image-ia/commit/f9373c6ee416e78468f6ab7821fd630713a66c9f))
  - migration alembic ([0e86239](https://github.com/studio-PAON-AVH/desc-image-ia/commit/0e862393ae3beeff175212e21eb8d9181c219ebb))
  - gestion refresh tokens ([8f24025](https://github.com/studio-PAON-AVH/desc-image-ia/commit/8f2402548a0fe9cf418df567b40ab683e646e0fe))
  - initialisation base de données ([3865095](https://github.com/studio-PAON-AVH/desc-image-ia/commit/3865095a489cc462c1a6d996a5e6d184ec0d88ee))
  - integration traitement epub sur interface Django ([63d20a9](https://github.com/studio-PAON-AVH/desc-image-ia/commit/63d20a90b5352a445e7af842b14f08c5f5dac55c))
  - extraction images EPUB ([8588990](https://github.com/studio-PAON-AVH/desc-image-ia/commit/858899055609b65a632290f16b1d0dee4d686caf))
  - tests unitaire et intégrations ([e493b1a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/e493b1a0a44e680a57d93990409b9ca3aefb7d1e))
  - communication django et fastapi ([b7bc132](https://github.com/studio-PAON-AVH/desc-image-ia/commit/b7bc1329faaa83ae458de18d7224f716af5e955d))
  - traitement par batch ([f2e9e1c](https://github.com/studio-PAON-AVH/desc-image-ia/commit/f2e9e1ccf814e6c106ba40eaf63dcb3a2b93368f))
  - mise en place extraction image EPUB ([89fa749](https://github.com/studio-PAON-AVH/desc-image-ia/commit/89fa7490e7e5262249f0e20285a539c82bc2e858))
  - support base64 encodage images ([b815bd3](https://github.com/studio-PAON-AVH/desc-image-ia/commit/b815bd3c4d5096de97223e5b0d92aa80e754805a))
  - ajout des dépendances ([750738c](https://github.com/studio-PAON-AVH/desc-image-ia/commit/750738cc66656a3712551fc79e6d53fd7f7762da))
  - initialisation de django ([38cbe23](https://github.com/studio-PAON-AVH/desc-image-ia/commit/38cbe235a6e1dfa59a1cdcf30f0925b64f26458f))
  - gestion des descriptions ([d2d9272](https://github.com/studio-PAON-AVH/desc-image-ia/commit/d2d927234345ae1163ac37dd455514451a06ac44))
  - ajout dockerfiles et requirements ([09660c4](https://github.com/studio-PAON-AVH/desc-image-ia/commit/09660c40bd7056c3102e8cd04c9b7382223381d2))

- #10:
  - modification du processus de traitement ([5806323](https://github.com/studio-PAON-AVH/desc-image-ia/commit/58063230c1e4d52337feb601533f52941b2bf5a8)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))

- #2:
  - integration du stockage des images ([eea73a1](https://github.com/studio-PAON-AVH/desc-image-ia/commit/eea73a17779b45ee0a36c50aeb5f8613fc52463e)) ([#7](https://github.com/studio-PAON-AVH/desc-image-ia/pull/7))
  - integration minio ([daae03d](https://github.com/studio-PAON-AVH/desc-image-ia/commit/daae03dc20f946d87ed4a55bdab3072c103eb66f)) ([#7](https://github.com/studio-PAON-AVH/desc-image-ia/pull/7))

- api:
  - communication entre les modèles et l'API ([4f95dbb](https://github.com/studio-PAON-AVH/desc-image-ia/commit/4f95dbb5c5ba7de774c2b45856e0931947159f75))
  - initialisation de l'api ([8bffbaf](https://github.com/studio-PAON-AVH/desc-image-ia/commit/8bffbaf9c87047905a2666482ee02b923d15301d))

### Bug Fixes

- general:
  - ajout du volume minio_data ([f874944](https://github.com/studio-PAON-AVH/desc-image-ia/commit/f874944014b87799b6c10c2ea7a70a18ca1f449c))
  - ajout de minio_data dans les volumes du `docker-compose.dev` ([1d81553](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1d8155392cd419df7d3d716b5e5f2c7b6baa0ed2)) ([#13](https://github.com/studio-PAON-AVH/desc-image-ia/pull/13))
  - modifiication des variables d'environnement pour MinIO ([97645a3](https://github.com/studio-PAON-AVH/desc-image-ia/commit/97645a3c09467588d1130fa37cc73ed2d80ff24f)) ([#13](https://github.com/studio-PAON-AVH/desc-image-ia/pull/13))
  - oublie du chemin de sorti ([5c2919b](https://github.com/studio-PAON-AVH/desc-image-ia/commit/5c2919bb561977044a874c547289096966534e57)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - correction du bug de limitation de débit sur les routes d'authentification ([40c74dc](https://github.com/studio-PAON-AVH/desc-image-ia/commit/40c74dc1572c250bdf3ae28372fb217134195594)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - mise à jour des dépendances ([bf0c964](https://github.com/studio-PAON-AVH/desc-image-ia/commit/bf0c964a3a3618f12b3d6afd293aa0ac4390efde)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - suppression du message de génération des descriptions ([bbaeac3](https://github.com/studio-PAON-AVH/desc-image-ia/commit/bbaeac38cc2c96e23b3e927963be73d47e3828dd)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - correction des tests integration ([f480b44](https://github.com/studio-PAON-AVH/desc-image-ia/commit/f480b44d8d4b400a9de7c8232d5989ef89bda0e9)) ([#8](https://github.com/studio-PAON-AVH/desc-image-ia/pull/8))
  - modification des workflows ([a91de35](https://github.com/studio-PAON-AVH/desc-image-ia/commit/a91de359b0b4c5c62e7bf620273ae4b96313b4ef)) ([#7](https://github.com/studio-PAON-AVH/desc-image-ia/pull/7))
  - correction de la copy du fichier environnement ([ac42a73](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ac42a73b450ad97c3ca11a59ce8e11f374471429)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - mise a jour de la configuration ([1480f1e](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1480f1ed34ecc6712e13bf7bcb1c489d01225e44)) ([#11](https://github.com/studio-PAON-AVH/desc-image-ia/pull/11))
  - mise a jour build redis ([e063979](https://github.com/studio-PAON-AVH/desc-image-ia/commit/e063979654687e8e84aa3a353b6b4e835c3555cc)) ([#7](https://github.com/studio-PAON-AVH/desc-image-ia/pull/7))
  - chemin dockerfile redis ([e4b586f](https://github.com/studio-PAON-AVH/desc-image-ia/commit/e4b586f863e718eee1c53fde1ff87dcfe4caeb9d)) ([#7](https://github.com/studio-PAON-AVH/desc-image-ia/pull/7))
  - correction configuration opentelemetry
- Modification de la configuration OpenTelemetry qui ne pointer pas sur le bon port
- Ajout des fichier d'environnement et ([613eaf5](https://github.com/studio-PAON-AVH/desc-image-ia/commit/613eaf563d3db06baa7f2dbd173d41e9409ae383)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - changement du tag image lgtm ([26e5bef](https://github.com/studio-PAON-AVH/desc-image-ia/commit/26e5bef613dce5cca44545f28051f00c574285a2)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - renommage chemin ghcr des images ([8a715a2](https://github.com/studio-PAON-AVH/desc-image-ia/commit/8a715a23f01c2b0fc978afc8116b21e3f6afbcef)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - correction du nommage vers ghcr ([b99f02a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/b99f02ac0b5ae59dfc2b4af57b0f56b07ffbef73)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - mise a jour du pipeline `test-deploy-dev.yml` ([997b93d](https://github.com/studio-PAON-AVH/desc-image-ia/commit/997b93d472f2d8d82ebaaf99ee230b119f870bd9)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - suppression du detecteur de changement ([8b7d74a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/8b7d74a36c241647c3c185aa161e65d968597870)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - correction installation dependance ([2e9cb3f](https://github.com/studio-PAON-AVH/desc-image-ia/commit/2e9cb3f624b988b5d9f5ffb851349f09e9205bc3)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - modification du nommage ([468c0ad](https://github.com/studio-PAON-AVH/desc-image-ia/commit/468c0ade043a7f3314ddff6baaa5eecc57348b39)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  - correction du test des cors ([0ab8a28](https://github.com/studio-PAON-AVH/desc-image-ia/commit/0ab8a28d2b1f462ce3bcc313c9bf5e639c84fa27)) ([#1](https://github.com/studio-PAON-AVH/desc-image-ia/pull/1))
  - correction installation des dependances ([e017967](https://github.com/studio-PAON-AVH/desc-image-ia/commit/e017967614b559c154b183d5f2fc234482edb1b4)) ([#1](https://github.com/studio-PAON-AVH/desc-image-ia/pull/1))
  - correction chemins des dependances ([5632033](https://github.com/studio-PAON-AVH/desc-image-ia/commit/5632033819cc46160930b1d31c0dea886e22415b)) ([#1](https://github.com/studio-PAON-AVH/desc-image-ia/pull/1))
  - correction erreur migration ([d588d2b](https://github.com/studio-PAON-AVH/desc-image-ia/commit/d588d2bdaa982339e3416ebb549420ff7ba2bf40))
  - optimisation des tâches et descriptions ([5389a26](https://github.com/studio-PAON-AVH/desc-image-ia/commit/5389a260c29dc4c49b5e921f2143cc4cbf4a2dd6))
  - correction logique metier ([de7b78a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/de7b78ae0e08de8aba15f07e775249c03a5e422e))
  - bug download ([72b0b37](https://github.com/studio-PAON-AVH/desc-image-ia/commit/72b0b3798fc79d0718f9286b3d02101a0630b0ca))
  - modification du schema de base de donnees ([62e23ca](https://github.com/studio-PAON-AVH/desc-image-ia/commit/62e23ca8c48e119102e290bb88d47c219905e7f9))
  - erreur mode package ([1265c0d](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1265c0d7a5c5a7f6f8ef407b6d043cd64a419a4c))
  - mise à jour des imports ([3afb690](https://github.com/studio-PAON-AVH/desc-image-ia/commit/3afb690a5151306d54ce838e4f1396c3eec5295c))
  - bug url api ([606d563](https://github.com/studio-PAON-AVH/desc-image-ia/commit/606d56329e1e626c8d58e8e2efdff653f99aba8d))
  - mise à jour pipeline CI ([bbd399d](https://github.com/studio-PAON-AVH/desc-image-ia/commit/bbd399d33bff285f1fb28ab8c0393978dbf316c3))
  - modification des versions python ([291a895](https://github.com/studio-PAON-AVH/desc-image-ia/commit/291a895aa2f5afd611a3ffc58ad84ac32c8ae841))
  - correction du pipeline CI ([ac0926d](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ac0926d02668aa57a9625ddb73cb96f1713a4ff7))
  - modification Dockerfiles et dépendances ([ea31632](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ea316323ec77e5816e02ea849ffb62bb5bd39e83))
  - mise à jour gestion traitement ([a513e2a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/a513e2ab09dede876c0810e0ea57c701213de78f))
  - mise à jour configuration Docker ([ecfcc9b](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ecfcc9b95d15c0811662a22e15fe2ed06afcbc30))
  - correction agregation par batch ([1f72e62](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1f72e6291cf751351038fea413d73656dac3df0e))
  - mise à jour dépendances et readme ([1225fcc](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1225fcc95c7e17d00069fd84575d4eab227bbf77))
  - correction de la coroutine ([6669386](https://github.com/studio-PAON-AVH/desc-image-ia/commit/666938696d9d144bd542122795825143f49e9fa3))
  - bug lors du type de l'image ([6e201b1](https://github.com/studio-PAON-AVH/desc-image-ia/commit/6e201b16c3254dd75b53f74406edb7d4d748f3a6))

- #9:
  - modification de l'ajout des descriptions
- Correction du traitement d'ajout des descriptions validées dans l'EPUB enrichi. La description doit être ajoutée dans le fichier HTML ou XHTML lié à l'image.
- fix(#10): modification de la barre de progression suite au changement vers le multi-worker. ([b1f14ea](https://github.com/studio-PAON-AVH/desc-image-ia/commit/b1f14eaf15210ede32ba189032512456d7e2fbea)) ([#12](https://github.com/studio-PAON-AVH/desc-image-ia/pull/12))

### Documentation

- general:
  - documentations de configuration serveur ([fec0b5f](https://github.com/studio-PAON-AVH/desc-image-ia/commit/fec0b5f5b4bcf216d21b0337bdcfc65b789516fe)) ([#6](https://github.com/studio-PAON-AVH/desc-image-ia/pull/6))
  - mise à jour ([1d270d5](https://github.com/studio-PAON-AVH/desc-image-ia/commit/1d270d575e4adc7776c149a538c94d6b850e03f4))

### Refactor

- general:
  - modification du workflow build ([ab56954](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ab56954e647544593ba665015a0b6be2b0c2910d)) ([#3](https://github.com/studio-PAON-AVH/desc-image-ia/pull/3))
  -  migration architecturale ([ce9a28a](https://github.com/studio-PAON-AVH/desc-image-ia/commit/ce9a28aeecbc0fa3da0566a1ffd105b55040fb5d))
  - modification structure ([08940d3](https://github.com/studio-PAON-AVH/desc-image-ia/commit/08940d3a97e97076d0e4faac0fa92eaf96d3b128))
  - refactorisation architecture backend ([7be624e](https://github.com/studio-PAON-AVH/desc-image-ia/commit/7be624ecc7fa6757caf12d839955f6f4904e7e79))

\* *This CHANGELOG was automatically generated by [auto-generate-changelog](https://github.com/BobAnkh/auto-generate-changelog)*
