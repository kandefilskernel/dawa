"""
Assistant « meilleur choix » de l'app : le patient écrit « J'ai besoin d'Amoxicilline, je suis à pied,
c'est urgent » et reçoit la pharmacie la plus rapide, le temps, et s'il vaut mieux réserver,
y aller ou se faire livrer.

Claude n'invente aucune donnée : il appelle l'outil `chercher_medicament`, qui renvoie les vrais
stocks, trajets, horaires, gardes et livraisons de l'API. Seuls le message et la liste des
pharmacies partent vers l'API (ni identifiant ni position exacte du patient).
Sans clé (ou si l'IA ne répond pas), une règle simple donne la même recommandation, sans phrase rédigée.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

import anthropic
from django.conf import settings

from catalogue.search import rechercher_medicaments
from pharmacies.trajets import MODES
from stock.delais import options_rapides

from .assistant import assistant_actif

journal = logging.getLogger(__name__)

# 3 appels au plus (recherche, éventuellement une 2e recherche, réponse) × 15 s : sous les 60 s de gunicorn.
DELAI_SECONDES = 15.0
TOURS_MAX = 3
LONGUEUR_MAX = 500

CONSIGNES = """Tu es l'assistant de l'application Uzima à Lubumbashi (RD Congo). Un patient cherche un \
médicament et veut l'obtenir le plus vite possible.

Utilise l'outil chercher_medicament avec le nom du médicament demandé (tel que le patient l'écrit). \
Il renvoie les pharmacies proches qui l'ont en stock, avec le délai réel pour l'obtenir à pied, à moto \
et en voiture (trajet par la route + attente si la pharmacie est fermée), le prix, la garde, la \
fiabilité du stock et la livraison (possible, durée, frais).

Puis recommande UN choix :
- la pharmacie (son id exact dans les résultats) et le mode de trajet du patient (s'il n'en dit rien : moto) ;
- l'action : « reserver » (la pharmacie met le médicament de côté, conseillé avant de se déplacer, \
surtout si le stock est à confirmer), « se_faire_livrer » (si la livraison est possible et plus rapide \
ou plus pratique, par exemple à pied et loin), « y_aller » ou « aucune » (rien trouvé).

Règles :
- Réponds dans la langue du patient (français, kiswahili ou anglais), en 2 à 4 phrases simples, sans \
titres ni listes. Donne le nom de la pharmacie, le temps et le prix.
- N'utilise que les données de l'outil : n'invente ni pharmacie, ni stock, ni prix, ni délai.
- Aucun diagnostic, aucun conseil de traitement ni de posologie. Si le message décrit des symptômes \
graves (difficulté à respirer, douleur forte, perte de connaissance, saignement, forte fièvre d'un \
jeune enfant, grossesse), mets orienter_medecin à true et dis d'aller tout de suite à l'hôpital ou \
chez un médecin.
- Si le médicament exige une ordonnance, rappelle-le.
- Si rien n'est trouvé, dis-le simplement et propose de créer une alerte dans l'app."""

OUTIL = {
    "name": "chercher_medicament",
    "description": "Pharmacies proches du patient qui ont ce médicament (ou un équivalent) en stock, "
                   "de la plus rapide à la plus lente, avec délais, prix, gardes et livraison.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"medicament": {"type": "string", "description": "Nom commercial ou DCI."}},
        "required": ["medicament"],
        "additionalProperties": False,
    },
}

ACTIONS = ("reserver", "se_faire_livrer", "y_aller", "aucune")

SCHEMA = {
    "type": "object",
    "properties": {
        "reponse": {"type": "string", "description": "Réponse au patient."},
        "pharmacie_id": {"type": "integer", "description": "id de la pharmacie conseillée, 0 si aucune."},
        "action": {"type": "string", "enum": list(ACTIONS)},
        "mode": {"type": "string", "enum": list(MODES)},
        "orienter_medecin": {"type": "boolean"},
    },
    "required": ["reponse", "pharmacie_id", "action", "mode", "orienter_medecin"],
    "additionalProperties": False,
}


class IAIndisponible(Exception):
    pass


@dataclass
class Choix:
    # Texte rédigé par l'IA ; vide avec la règle simple (l'app compose alors la phrase dans la langue choisie).
    reponse: str
    source: str  # "ia" ou "regles"
    situation: str = "trouve"  # trouve, medicament_inconnu, introuvable
    medicament: object = None
    option: object = None  # Stock annoté (acces, livraison) de la pharmacie conseillée
    action: str = "aucune"
    mode: str = "moto"
    orienter_medecin: bool = False
    autres: list = field(default_factory=list)


# --- Données réelles -------------------------------------------------------------------------------

def _sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")


MOTS_VIDES = {
    "besoin", "cherche", "chercher", "trouver", "veux", "voudrais", "urgent", "urgence", "vite", "rapide",
    "rapidement", "suis", "pied", "moto", "voiture", "taxi", "livrer", "livraison", "pharmacie", "medicament",
    "medicaments", "comprime", "comprimes", "sirop", "pour", "avec", "dans", "mais", "chez", "moi", "mon", "fils",
    "fille", "enfant", "need", "want", "urgently", "foot", "walking", "car", "please", "nahitaji", "dawa",
    "haraka", "tafadhali", "kwa", "miguu", "pikipiki", "gari", "naomba",
}


def trouver_medicament(texte):
    """Le médicament le plus probable dans une phrase libre (mot par mot, puis paires de mots)."""
    mots = [m for m in re.findall(r"[\w-]+", _sans_accents(texte)) if len(m) >= 4 and m not in MOTS_VIDES]
    candidats = [*mots, *(f"{a} {b}" for a, b in zip(mots, mots[1:]))]
    meilleur = None
    for terme in candidats:
        m = rechercher_medicaments(terme).first()
        similarite = getattr(m, "similarite", 0) if m else 0
        if m and similarite >= 0.4 and (meilleur is None or similarite > meilleur[0]):
            meilleur = (similarite, m)
    return meilleur[1] if meilleur else None


def options_pour(medicament, depart):
    return options_rapides(medicament, depart) if medicament else []


def _resume_option(s):
    a = s.acces
    return {
        "pharmacie_id": s.pharmacie_id,
        "pharmacie": s.pharmacie.nom,
        "quartier": s.pharmacie.quartier,
        "produit": f"{s.medicament.nom_commercial} {s.medicament.dosage}".strip(),
        "prix_fc": s.prix,
        "de_garde": s.de_garde,
        "ouverte": a["ouverte"],
        "ouvre_dans_min": a["ouvre_dans_min"],
        "delai_min": a["delai_min"],
        "distance_route_km": {m: t["distance_km"] for m, t in a["trajets"].items()},
        "stock_confirme_recemment": s.est_confirme,
        "livraison": s.livraison,
    }


def resultat_outil(nom, depart):
    medicament = rechercher_medicaments(nom).first() if len(nom.strip()) >= 2 else None
    options = options_pour(medicament, depart)
    return medicament, options, {
        "medicament": None if medicament is None else {
            "nom": f"{medicament.nom_commercial} {medicament.dosage}".strip(), "dci": medicament.dci,
            "ordonnance_requise": medicament.ordonnance_requise,
        },
        "pharmacies": [_resume_option(s) for s in options],
    }


# --- Règle simple (sans IA) ------------------------------------------------------------------------

def mode_dans(texte):
    t = _sans_accents(texte)
    if re.search(r"\b(a pied|pied|marche|walking|on foot|kwa miguu|miguu)\b", t):
        return "pied"
    if re.search(r"\b(voiture|taxi|car|gari)\b", t):
        return "voiture"
    return "moto"


def veut_livraison(texte):
    return bool(re.search(r"\b(livr\w*|deliver\w*|kuletewa|niletee)\b", _sans_accents(texte)))


def choix_par_regles(message, depart, medicament=None, options=None):
    if options is None:
        medicament = trouver_medicament(message)
        options = options_pour(medicament, depart)
    mode = mode_dans(message)
    if medicament is None:
        return Choix("", "regles", "medicament_inconnu", mode=mode)
    if not options:
        return Choix("", "regles", "introuvable", medicament=medicament, mode=mode)

    def delai(s):
        d = s.acces["delai_min"][mode]
        return d if d is not None else float("inf")

    meilleure = min(options, key=delai)
    livrables = [s for s in options if s.livraison["minutes"] is not None]
    livraison = min(livrables, key=lambda s: s.livraison["minutes"], default=None)
    action = "reserver"
    if livraison and (veut_livraison(message) or livraison.livraison["minutes"] < delai(meilleure)):
        meilleure, action = livraison, "se_faire_livrer"
    autres = [s for s in options if s is not meilleure][:2]
    return Choix("", "regles", "trouve", medicament, meilleure, action, mode, False, autres)


# --- Avec Claude -----------------------------------------------------------------------------------

def _client():
    return anthropic.Anthropic(api_key=settings.ASSISTANT_IA_CLE, timeout=DELAI_SECONDES, max_retries=0)


def _appeler(messages):
    try:
        return _client().beta.messages.create(
            model=settings.ASSISTANT_IA_MODELE,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=CONSIGNES,
            tools=[OUTIL],
            messages=messages,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except anthropic.APIStatusError as e:
        journal.warning("Assistant choix : erreur API %s", e.status_code)
        raise IAIndisponible from e
    except anthropic.APIConnectionError as e:
        journal.warning("Assistant choix : connexion impossible")
        raise IAIndisponible from e


def choix_par_ia(message, depart):
    messages = [{"role": "user", "content": message}]
    trouves = {}  # pharmacie_id → option, pour toutes les recherches de l'outil
    medicament = None
    for _ in range(TOURS_MAX):
        resultat = _appeler(messages)
        if resultat.stop_reason in ("refusal", "max_tokens"):
            raise IAIndisponible(resultat.stop_reason)
        appels = [b for b in resultat.content if b.type == "tool_use"]
        if resultat.stop_reason != "tool_use" or not appels:
            break
        messages.append({"role": "assistant", "content": resultat.content})
        reponses = []
        for appel in appels:
            m, options, donnees = resultat_outil(str(appel.input.get("medicament", ""))[:100], depart)
            medicament = medicament or m
            trouves.update({s.pharmacie_id: s for s in options})
            reponses.append({"type": "tool_result", "tool_use_id": appel.id,
                             "content": json.dumps(donnees, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": reponses})
    else:
        raise IAIndisponible("trop d'appels d'outil")

    texte = next((b.text for b in resultat.content if b.type == "text"), "")
    try:
        d = json.loads(texte)
    except json.JSONDecodeError as e:
        raise IAIndisponible("réponse illisible") from e
    option = trouves.get(d["pharmacie_id"])  # un id absent des résultats de l'outil est ignoré
    action = d["action"] if option is not None else "aucune"
    autres = [s for s in trouves.values() if s is not option][:2]
    situation = "trouve" if option else ("introuvable" if medicament else "medicament_inconnu")
    return Choix(d["reponse"].strip()[:1500], "ia", situation, medicament, option, action,
                 d["mode"] if d["mode"] in MODES else "moto", bool(d["orienter_medecin"]), autres)


def meilleur_choix(message, depart):
    if assistant_actif():
        try:
            return choix_par_ia(message, depart)
        except IAIndisponible:
            pass  # on répond quand même, avec la règle simple
    return choix_par_regles(message, depart)
