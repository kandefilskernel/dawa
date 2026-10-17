# Mettre Uzima en ligne

Ce guide installe le site web (espaces des pharmacies, des établissements de santé et de l'équipe Uzima,
API de l'app) sur un serveur loué, avec un nom de domaine et le HTTPS automatique.

```
Internet ──HTTPS──> Caddy (certificat automatique)
                     ├─ pages du site ───────────────> Next.js (dossier web/)
                     ├─ /api, /admin, /livreur ───────> Django/gunicorn ──> PostgreSQL + PostGIS
                     │  (et le téléchargement des pièces KYC, réservé à l'équipe)
                     ├─ sert /static et /media (photos)
                     └─ ne sert JAMAIS les pièces KYC directement (dossier prive/)
```

Les anciennes adresses (`/portail/…`, `/etablissement/…`, `/dawa/…`) sont redirigées vers les nouvelles pages,
y compris les liens « mot de passe oublié » déjà envoyés.

## 1. Ce qu'il faut acheter

| Quoi | Exemple | Ordre de prix |
|---|---|---|
| Un serveur (VPS) Linux **Ubuntu 24.04**, 2 processeurs, 4 Go de mémoire, 40 Go de disque | Hetzner, OVHcloud, Contabo, DigitalOcean, ou un hébergeur congolais | 5 à 25 $ / mois |
| Un nom de domaine | `dawa.cd`, `dawa-sante.com`… | 10 à 40 $ / an |

Choisissez un centre de données proche de l'Afrique centrale ou de l'Europe pour de meilleurs temps de réponse.

## 2. Faire pointer le domaine vers le serveur

Chez le vendeur du domaine, créez un enregistrement DNS :

- Type **A**, nom `@` (ou `dawa` pour `dawa.mondomaine.cd`), valeur : **l'adresse IP du serveur**.

Attendez que `ping votre-domaine` réponde avec cette IP (de quelques minutes à quelques heures).

## 3. Préparer le serveur (une seule fois)

Connectez-vous en SSH (`ssh root@IP-du-serveur`), puis :

```sh
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh          # installe Docker et Docker Compose
ufw allow OpenSSH && ufw allow 80 && ufw allow 443/tcp && ufw allow 443/udp && ufw enable
git clone https://github.com/<votre-compte>/dawa.git /opt/dawa
cd /opt/dawa/deploy
```

## 4. Configurer

```sh
cp .env.prod.example .env.prod
nano .env.prod
```

Remplissez au minimum :

- `DAWA_DOMAINE`, `DJANGO_ALLOWED_HOSTS` : votre domaine (ex. `dawa.cd`) ;
- `DJANGO_CSRF_TRUSTED_ORIGINS` : `https://` + votre domaine ;
- `DAWA_EMAIL_ADMIN` : un e-mail réel (alertes des certificats HTTPS) ;
- `DJANGO_SECRET_KEY` et `DATABASE_PASSWORD` : générez-les avec les commandes indiquées dans le fichier ;
- `DAWA_NUMERO_PAIEMENT` : le numéro mobile money qui reçoit les abonnements ;
- `EMAIL_*` : un service d'envoi d'e-mails (Brevo, Mailjet… ont une offre gratuite) — indispensable pour
  « mot de passe oublié » et les alertes ;
- `DAWA_ALERTES_EMAILS` : qui reçoit un e-mail à chaque erreur du serveur.

`.env.prod` contient des secrets : il est ignoré par Git, ne le copiez nulle part ailleurs.

## 5. Démarrer

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend   # Ctrl+C pour quitter
```

Au premier démarrage, le serveur crée la base, prépare les fichiers du site et **génère sa propre clé RSA**
(celle de votre PC n'est jamais envoyée). Caddy obtient le certificat HTTPS tout seul.

Créez ensuite le compte administrateur et le compte de l'équipe Dawa :

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py createsuperuser
```

Ce compte se connecte sur `https://votre-domaine/connexion` et arrive dans l'espace de l'équipe (`/equipe`).
Pour d'autres membres de l'équipe : créez-les dans `/admin/` et cochez « Statut équipe ».

Ne lancez **pas** `seed_demo` en production : il crée des pharmacies fictives.
Les médicaments du catalogue s'ajoutent dans `/admin/` (Catalogue › Médicaments) ; leurs illustrations :

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py generer_images
```

Vérifiez que les e-mails partent (l'équipe doit recevoir un message de test) :

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py sendtestemail --admins
```

## 6. Les liens

- Connexion des professionnels : `https://votre-domaine/connexion`
- Inscription d'une pharmacie : `https://votre-domaine/inscription/pharmacie`
- Inscription d'un hôpital, d'une clinique ou d'un centre de santé : `https://votre-domaine/inscription/etablissement`
- Espace de l'équipe Uzima : `https://votre-domaine/equipe`
- Administration technique (catalogue, grossistes, gardes) : `https://votre-domaine/admin/`
- API de l'app : `https://votre-domaine/api/`

## 7. Relier l'application mobile

Sur GitHub : **Actions › APK Android › Run workflow**, et saisissez `https://votre-domaine` dans
« Adresse de l'API ». L'APK publié dans la Release appellera alors le serveur en ligne.
Pensez aussi à changer la valeur par défaut `api_url` dans `.github/workflows/apk.yml`.

**Notifications (Firebase)** : copiez le fichier du compte de service dans le volume des clés, puis redémarrez :

```bash
docker compose -f docker-compose.prod.yml cp firebase.json backend:/app/cles/firebase.json
docker compose -f docker-compose.prod.yml restart backend
```

Il est sauvegardé avec la clé RSA. Voir « Notifications sur le téléphone » dans le README pour créer le projet Firebase.

## 8. Sauvegardes (indispensable)

`sauvegarde.sh` copie la base, les photos, les **pièces KYC** et la **clé RSA** (la perdre déconnecte tous les téléphones).

```sh
chmod +x /opt/dawa/deploy/sauvegarde.sh
/opt/dawa/deploy/sauvegarde.sh                 # test : crée /var/backups/dawa/base_….dump et fichiers_….tar.gz
crontab -e                                     # puis ajoutez la ligne :
30 2 * * * /opt/dawa/deploy/sauvegarde.sh >> /var/log/dawa-sauvegarde.log 2>&1
```

Les 14 derniers jours sont gardés sur le serveur. **Copiez-les aussi ailleurs** (autre serveur, stockage en ligne) :
un serveur peut tomber en panne avec ses sauvegardes. Ces fichiers contiennent des données sensibles
(pièces d'identité) : stockage chiffré et accès limité.

Restaurer la base : `pg_restore --clean -U dawa -d dawa base_XXXX.dump` dans le conteneur `db`.

## 9. Mettre à jour le site

```sh
cd /opt/dawa && git pull
cd deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Les migrations s'appliquent automatiquement au redémarrage.

## Points de vigilance

- **Mot de passe oublié** : chaque structure reçoit un lien par e-mail. Sans e-mail, l'équipe crée un lien depuis
  `/equipe` (Pharmacies ou Santé, bouton « Lien mot de passe ») et l'envoie par WhatsApp ou SMS **au numéro officiel**, après avoir
  vérifié l'identité de la personne.
- **Tentatives de connexion** : 5 échecs sur un identifiant (ou 30 depuis une même connexion) bloquent 15 minutes.

- Quand le HTTPS fonctionne depuis quelques jours, passez `DJANGO_HSTS_SECONDES=31536000` dans `.env.prod`.
- Mettez à jour le serveur chaque mois : `apt update && apt upgrade -y`.
- Les pièces KYC sont des données personnelles : renseignez-vous sur les obligations de protection des données
  applicables en RDC et indiquez aux structures pourquoi et combien de temps vous les conservez.
