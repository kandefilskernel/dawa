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
    "gestion",
    "kyc",
    "verification",
    "conseil",
    "abonnements",
    "grossistes",
    "messagerie",
    "notifications",
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

AUTHENTICATION_BACKENDS = ["config.securite.ConnexionLimitee"]
# Vrai derrière Caddy : l'IP du client est lue dans X-Forwarded-For (limites de tentatives).
DERRIERE_PROXY = os.environ.get("DAWA_DERRIERE_PROXY", "0") == "1"
LOGIN_URL = "portail:connexion"
PASSWORD_RESET_TIMEOUT = 24 * 3600  # liens « mot de passe oublié » valables 24 h
LOGIN_REDIRECT_URL = "portail:tableau"
LOGOUT_REDIRECT_URL = "portail:connexion"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# Pièces justificatives (KYC) : hors de MEDIA_ROOT, jamais servies publiquement.
KYC_RACINE = Path(os.environ.get("KYC_RACINE", BASE_DIR / "prive"))
TESTS = sys.argv[1:2] == ["test"]
if TESTS:
    # Les tests génèrent des images : on ne pollue pas le vrai dossier media.
    MEDIA_ROOT = Path(tempfile.gettempdir()) / "dawa-tests-media"
    KYC_RACINE = Path(tempfile.gettempdir()) / "dawa-tests-prive"
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

# Serveur de routage OSRM (distances par la route, données OpenStreetMap). Vide : estimation seule.
# Par défaut le serveur public de FOSSGIS (profils routed-foot / routed-car) ; jamais en test.
ROUTAGE_URL = "" if TESTS else os.environ.get("UZIMA_ROUTAGE_URL", "https://routing.openstreetmap.de").rstrip("/")

# Abonnements des pharmacies (montants mensuels en FC, à ajuster après le terrain).
ABONNEMENT_PRIX_FC = {"essentiel": 30_000, "visibilite": 75_000}
# Numéro mobile money Uzima où les pharmacies paient leur abonnement.
DAWA_NUMERO_PAIEMENT = os.environ.get("DAWA_NUMERO_PAIEMENT", "à configurer")
# Nombre maximum de résultats sponsorisés en tête d'une recherche.
MAX_RESULTATS_SPONSORISES = 2

# Webhook SMS / WhatsApp : jeton secret partagé avec le fournisseur (Africa's Talking, Twilio…).
MESSAGERIE_JETON = os.environ.get("MESSAGERIE_JETON", "")

# Notifications sur le téléphone (Firebase Cloud Messaging). Désactivées sans compte de service.
# Contenu JSON du compte de service, ou fichier (par défaut backend/cles/firebase.json, ignoré par git).
FIREBASE_COMPTE_SERVICE = os.environ.get("FIREBASE_COMPTE_SERVICE", "")
FIREBASE_COMPTE_SERVICE_FICHIER = Path(
    os.environ.get("FIREBASE_COMPTE_SERVICE_FICHIER", BASE_DIR / "cles" / "firebase.json")
)
# En test, envoi immédiat (pas de fil séparé) pour pouvoir le vérifier.
NOTIFICATIONS_SYNCHRONES = TESTS

# Assistant IA du portail (brouillons de réponses aux questions). Désactivé sans clé.
ASSISTANT_IA_CLE = os.environ.get("ANTHROPIC_API_KEY", "")
ASSISTANT_IA_MODELE = os.environ.get("DAWA_ASSISTANT_MODELE", "claude-opus-5-5")

# --- Production (DJANGO_DEBUG=0 derrière le proxy HTTPS Caddy, voir deploy/) ---
if not DEBUG and not TESTS:
    from django.core.exceptions import ImproperlyConfigured

    if SECRET_KEY in ("", "dev-insecure", "change-moi-en-production") or len(SECRET_KEY) < 40:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être une valeur secrète longue en production.")
    # Caddy termine le HTTPS et transmet X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDES", "3600"))
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    # L'app mobile native n'a pas besoin de CORS ; la version web de l'app, si elle est publiée ailleurs, oui.
    CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("DJANGO_CORS_ORIGINES", "").split(",") if o]

# E-mails : liens « mot de passe oublié » et alertes d'erreur. Sans serveur SMTP, ils s'affichent dans les logs.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_UTILISATEUR", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_MOT_DE_PASSE", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_TLS", "1") == "1"
EMAIL_TIMEOUT = 15
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
                 else "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = SERVER_EMAIL = os.environ.get("EMAIL_EXPEDITEUR", "Uzima <ne-pas-repondre@localhost>")
EMAIL_SUBJECT_PREFIX = "[Uzima] "
# Destinataires des alertes d'erreur serveur (500), ex. « Équipe:equipe@dawa.cd,Autre:autre@dawa.cd ».
ADMINS = [tuple(a.split(":", 1)) for a in os.environ.get("DAWA_ALERTES_EMAILS", "").split(",") if ":" in a]

# Cache partagé entre les processus gunicorn (limites de tentatives, limites de l'API).
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"} if DEBUG or TESTS
    else {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "dawa_cache"}
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"hors_debug": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        # Toute erreur 500 envoie un e-mail aux ADMINS (avec la trace), en production uniquement.
        "alerte_email": {"class": "django.utils.log.AdminEmailHandler", "level": "ERROR",
                         "filters": ["hors_debug"], "include_html": False},
    },
    "loggers": {
        "django.request": {"handlers": ["console", "alerte_email"], "level": "ERROR", "propagate": False},
        "dawa.securite": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_NIVEAU", "WARNING")},
}
