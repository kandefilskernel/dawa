# Dawa

Trouver un médicament dans une pharmacie proche — Lubumbashi.

```
backend/   API Django + PostGIS, back-office admin
mobile/    App patient Flutter (à venir)
web/       Site Next.js des pharmacies, établissements de santé et de l'équipe
```

## Lancer le backend

Prérequis : Docker Desktop démarré.

```powershell
Copy-Item .env.example .env      # une seule fois
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo      # données fictives
docker compose exec backend python manage.py createsuperuser
```

- Admin : http://localhost:8010/admin/
- API : http://localhost:8010/api/

Tests :

```powershell
docker compose exec backend python manage.py test
```

## Sécurité : jetons d'appareil signés RSA

L'app n'envoie plus un identifiant libre : le serveur lui délivre un jeton **JWT RS256** signé avec sa clé privée RSA (3072 bits).
Un jeton fabriqué, modifié, expiré ou signé avec un autre algorithme est refusé (401).

```powershell
docker compose exec backend python manage.py generer_cle_rsa   # une seule fois, crée backend/cles/jwt_prive.pem
```

- `POST /api/appareil/jeton/` : premier lancement (nouvel appareil) ou renouvellement (avec `Authorization: Bearer …`).
- Appels suivants : en-tête `Authorization: Bearer <jeton>`. Durée : 180 jours (`JWT_DUREE_JOURS`), l'app renouvelle tous les 30 jours.
- **Production** : fournir la clé via `JWT_CLE_PRIVEE` ou `JWT_CLE_PRIVEE_FICHIER` (sans clé, le serveur refuse d'émettre ou de vérifier des jetons). Ne jamais versionner la clé ; la perdre ou la changer déconnecte tous les téléphones.
- Transition : `DAWA_ACCEPTER_ANCIEN_CLIENT_ID=1` accepte encore l'ancien `X-Client-Id` et permet aux anciennes installations d'échanger leur identifiant contre un jeton sans perdre leurs réservations. Remettre à `0` ensuite.

## Langues de l'app (français, swahili, anglais)

Au premier lancement, l'app demande la langue ; on la change ensuite dans « Mon espace ».
Les textes restent écrits en français dans le code, entourés de `tr('…')` ; leurs traductions sont dans
`mobile/lib/traductions/sw.dart` et `en.dart`. Après avoir ajouté ou modifié un texte :

```powershell
cd mobile; flutter test   # signale tout texte sans traduction swahili ou anglaise
```

Le swahili utilisé est le swahili standard : à faire relire par une personne de Lubumbashi.
La recherche à la voix (bouton micro) utilise la reconnaissance vocale du téléphone, dans la langue choisie si le téléphone la connaît.

## Images des médicaments

Chaque médicament a une image, affichée dans l'app (mise en cache sur le téléphone) et dans le portail.

- **Illustrations automatiques** : `seed_demo` les génère ; pour les nouveaux médicaments :
  `docker compose exec backend python manage.py generer_images`
  (`--regenerer` pour refaire les illustrations après un changement de nom ou de dosage ; les vraies photos ne sont jamais écrasées).
- **Vraies photos en masse** : déposer les photos dans `backend/images_a_importer/`, nommées selon le médicament, puis :
  ```powershell
  docker compose exec backend python manage.py importer_images --lister       # noms de fichiers attendus
  docker compose exec backend python manage.py importer_images --simulation   # vérifier sans rien modifier
  docker compose exec backend python manage.py importer_images                # importer
  ```
  Noms reconnus : `doliprane-500-mg.jpg` (nom + dosage), `doliprane.jpg` (si le nom est unique), le code-barres, ou l'identifiant.
  Formats JPG, PNG, WebP ; chaque photo est redressée, réduite à 800 px et convertie en WebP (≈ 20–60 Ko).
- **Une photo à la fois** : admin → Médicaments → champ « Image ».

Utilisez uniquement des photos que vous avez prises vous-mêmes (boîtes achetées localement) ou fournies avec l'accord du laboratoire.

## Site des professionnels (Next.js)

`docker compose up -d web` puis http://localhost:3000 — site sans application à installer, fait pour le téléphone
(dossier `web/`, voir `web/README.md`). Il parle à Django par `/api/web/`. Trois espaces :

- `/pharmacie` : portail des pharmacies (détail ci-dessous), inscription sur `/inscription/pharmacie` ;
- `/sante` : hôpitaux, cliniques, centres de santé, laboratoires, maternités (fiche, justificatifs),
  inscription sur `/inscription/etablissement` ;
- `/equipe` : équipe Uzima (inscriptions et pièces KYC, visibilité, liens de mot de passe, abonnements, signalements).

Les anciennes pages Django (`/portail/`, `/etablissement/`, `/dawa/`) existent encore en local ; en production,
Caddy les redirige vers le nouveau site. La page du livreur (`/livreur/<jeton>/`) reste servie par Django.

Portail des pharmacies :

- **Accueil** : réservations à traiter, état du stock, médicaments recherchés à moins de 5 km mais absents du stock.
- **Réservations** : accepter → marquer prête (redonne 2 h au client) → retirée, ou refuser avec un motif. Actualisation automatique.
- **Stock** : interrupteur disponible / rupture et prix, enregistrés instantanément ; « Tout est à jour » pour confirmer le stock.
- **Questions** : questions des patients, partagées entre pharmacies ; le premier qui répond la prend (option « orienter vers un médecin »).
- **Pharmacie** : téléphone, WhatsApp, horaires ; prochaines gardes.

Créer un accès : dans l'admin, créer un utilisateur, puis un **Pharmacien** qui le rattache à sa pharmacie.
Compte de démo : `pharmacie-centre`, créé par `seed_demo` avec le mot de passe défini dans `.env` (`DAWA_DEMO_MOT_DE_PASSE`).

## Notifications sur le téléphone (Firebase)

Le patient est prévenu quand sa réservation est acceptée, prête, en livraison ou refusée, quand un médicament
de ses alertes redevient disponible, et quand un pharmacien répond à sa question — dans la langue de l'app.
Sans configuration, tout fonctionne sans notifications (les alertes restent visibles dans « Mon espace »).

1. Sur https://console.firebase.google.com : créer un projet, puis **ajouter une app Android** avec le nom de
   package `cd.dawa.dawa` (le fichier `google-services.json` proposé n'est pas nécessaire).
2. **App mobile** : les valeurs du projet `dawa-44a42` (tirées de `google-services.json`) sont déjà dans
   `.github/workflows/apk.yml`. Pour un autre projet, les remplacer, ou définir dans GitHub → Settings → Secrets
   and variables → Actions → **Variables** : `FIREBASE_API_KEY`, `FIREBASE_APP_ID`, `FIREBASE_SENDER_ID`,
   `FIREBASE_PROJECT_ID`. En local :
   `flutter run --dart-define=FIREBASE_API_KEY=… --dart-define=FIREBASE_APP_ID=… --dart-define=FIREBASE_SENDER_ID=… --dart-define=FIREBASE_PROJECT_ID=…`
3. **Serveur** : Paramètres du projet → Comptes de service → **Générer une nouvelle clé privée**. Enregistrer le
   fichier sous `backend/cles/firebase.json` (ignoré par git, à ne jamais partager), puis
   `docker compose restart backend`.

`POST /api/appareil/notifications/` enregistre le jeton du téléphone (`{"jeton": "…", "langue": "fr"}`) ;
les téléphones désinstallés sont oubliés automatiquement. Android uniquement pour l'instant.

## Lancer l'app mobile (Flutter)

Le backend doit tourner (voir ci-dessus).

```powershell
cd mobile
flutter run -d chrome                 # dans le navigateur
flutter run                           # sur l'émulateur Android ou un téléphone branché
```

Sur un vrai téléphone, l'API doit être joignable : passer l'adresse IP du PC sur le Wi-Fi :
`flutter run --dart-define=API_URL=http://192.168.1.20:8010`

Fonctionnalités patient :

- **Recherche** avec autocomplétion, ou **scan du code-barres** de la boîte.
- **Résultats** en liste ou sur carte, réservation, appel, itinéraire ; alerte « me prévenir » si introuvable.
- **Vérifier un lot** (anti-contrefaçon) et **signaler un produit suspect** avec photo.
- **Pharmacien en ligne** : questions simples, réponses des pharmaciens partenaires (pas de diagnostic).
- **Rappels de traitement** : prises du jour à cocher, notifications programmées (Android), fin de traitement.
- **Pharmacies de garde** (disponibles hors ligne), **annuaire santé**, **Mon espace** (réservations, alertes, traitements, favoris).

Écrans : recherche avec autocomplétion → résultats (liste / carte, rayon 2–20 km, appel direct) ; onglet « De garde ».

## API

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/recherche/?medicament=12&lat=-11.66&lng=27.48&rayon=5` | Pharmacies ayant ce médicament ou un équivalent (même DCI, même forme), triées par distance — ou par prix sans position |
| GET | `/api/recherche/?q=amoxicilline&lat=...&lng=...` | Idem, à partir du texte tapé (meilleure correspondance) |
| GET | `/api/medicaments/?q=dolip` | Autocomplétion (tolère fautes et accents) |
| GET | `/api/medicaments/?code_barres=...` | Scan d'une boîte |
| GET | `/api/pharmacies/?lat=&lng=&rayon=` | Pharmacies proches |
| GET | `/api/pharmacies/garde/?lat=&lng=` | Pharmacies de garde en ce moment |

| GET | `/api/pharmacies/{id}/stock/?q=` | Produits disponibles dans une pharmacie |
| GET | `/api/etablissements/?type=hopital&urgences=1&lat=&lng=` | Annuaire santé (hôpitaux, cliniques, labos, maternités) |
| GET / POST | `/api/reservations/` | Réservations de l'appareil (mise de côté 2 h) |
| POST | `/api/reservations/{id}/annuler/` | Annuler une réservation active |
| GET / POST | `/api/alertes/` | Alertes « prévenez-moi quand c'est disponible » |
| DELETE | `/api/alertes/{id}/` | Supprimer une alerte |

Les routes réservations et alertes exigent l'en-tête `X-Client-Id` (UUID généré par l'app au premier lancement,
en attendant la connexion par SMS). Une alerte se déclenche automatiquement quand une pharmacie à portée
signale le médicament (ou un équivalent) disponible.

Les pharmacies gèrent les réservations depuis l'admin : actions « Accepter », « Marquer prête », « Marquer retirée », « Refuser ».

| GET | `/api/verification/?lot=AB123` | Statut d'un lot : conforme, expiré, rappelé, contrefait, inconnu |
| GET / POST | `/api/signalements/` | Signalements de produits suspects (multipart, photo facultative) |
| GET / POST | `/api/questions/` | Questions au pharmacien |

Lots et signalements se gèrent dans l'admin (section Anti-contrefaçon). La base des lots doit être alimentée à partir
de sources officielles (autorité pharmaceutique, alertes de rappel, fabricants) : un lot « inconnu » n'est pas un lot faux.
Lots de démonstration : `DEMO-C001` (conforme), `DEMO-C666` (contrefait), `DEMO-A777` (rappelé), `DEMO-D100` (périmé).

Chaque résultat indique `confirme: false` si le stock n'a pas été mis à jour depuis 48 h.
