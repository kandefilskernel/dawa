import os
import sys
import tempfile
from pathlib import Path

from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.postgres",
    "django.contrib.humanize",
    "rest_framework",
    "corsheaders",
    "catalogue",
    "pharmacies",
    "stock",
    "reservations",
    "sante",
    "portail",
    "verification",
    "conseil",
    "abonnements",
    "grossistes",
    "messagerie",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "NAME": os.environ.get("DATABASE_NAME", "dawa"),
        "USER": os.environ.get("DATABASE_USER", "dawa"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "dawa"),
        # Connexions réutilisées entre requêtes (évite une reconnexion à chaque appel).
        "CONN_MAX_AGE": int(os.environ.get("DATABASE_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Lubumbashi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

LOGIN_URL = "portail:connexion"
LOGIN_REDIRECT_URL = "portail:tableau"
LOGOUT_REDIRECT_URL = "portail:connexion"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
TESTS = sys.argv[1:2] == ["test"]
if TESTS:
    # Les tests génèrent des images : on ne pollue pas le vrai dossier media.
    MEDIA_ROOT = Path(tempfile.gettempdir()) / "dawa-tests-media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_HEADERS = (*default_headers, "x-client-id")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["config.client.JetonAppareil"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {"jeton_appareil": "30/hour"},
}

# Jetons d'appareil signés RSA (RS256). Clé privée : contenu PEM dans JWT_CLE_PRIVEE,
# ou fichier (par défaut backend/cles/jwt_prive.pem, créé par `manage.py generer_cle_rsa`).
JWT_CLE_PRIVEE = os.environ.get("JWT_CLE_PRIVEE", "").replace("\\n", "\n")  # PEM sur une ligne dans .env
JWT_CLE_PRIVEE_FICHIER = Path(os.environ.get("JWT_CLE_PRIVEE_FICHIER", BASE_DIR / "cles" / "jwt_prive.pem"))
JWT_DUREE_JOURS = int(os.environ.get("JWT_DUREE_JOURS", "180"))
# Transition : accepter encore l'ancien en-tête X-Client-Id non signé. À désactiver dès que possible.
ACCEPTER_ANCIEN_CLIENT_ID = os.environ.get("DAWA_ACCEPTER_ANCIEN_CLIENT_ID", "0") == "1"

# Au-delà de ce délai sans mise à jour, une disponibilité est affichée « non confirmée ».
STOCK_FRAICHEUR_HEURES = 48

# Livraison à moto : forfait + prix au kilomètre, distance maximale.
LIVRAISON_FORFAIT_FC = 2000
LIVRAISON_PRIX_KM_FC = 500
LIVRAISON_DISTANCE_MAX_KM = 15

# Abonnements des pharmacies (montants mensuels en FC, à ajuster après le terrain).
ABONNEMENT_PRIX_FC = {"essentiel": 30_000, "visibilite": 75_000}
# Numéro mobile money Dawa où les pharmacies paient leur abonnement.
DAWA_NUMERO_PAIEMENT = os.environ.get("DAWA_NUMERO_PAIEMENT", "à configurer")
# Nombre maximum de résultats sponsorisés en tête d'une recherche.
MAX_RESULTATS_SPONSORISES = 2

# Webhook SMS / WhatsApp : jeton secret partagé avec le fournisseur (Africa's Talking, Twilio…).
MESSAGERIE_JETON = os.environ.get("MESSAGERIE_JETON", "")

# Assistant IA du portail (brouillons de réponses aux questions). Désactivé sans clé.
ASSISTANT_IA_CLE = os.environ.get("ANTHROPIC_API_KEY", "")
ASSISTANT_IA_MODELE = os.environ.get("DAWA_ASSISTANT_MODELE", "claude-opus-5-5")
