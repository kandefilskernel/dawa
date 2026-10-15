"""
Assistant IA du portail : propose un BROUILLON de réponse à une question de patient.

Le pharmacien relit, corrige et envoie lui-même ; rien n'est jamais envoyé au patient sans lui.
Seuls le texte de la question et la fiche du médicament partent vers l'API (aucun identifiant patient).
"""
import json
import logging
from dataclasses import dataclass

import anthropic
from django.conf import settings

journal = logging.getLogger(__name__)

CONSIGNES = """Tu aides un pharmacien d'officine de Lubumbashi (RD Congo) à répondre aux questions \
simples envoyées par des patients via l'application Dawa (notice, prise, conservation, interactions courantes).

Tu rédiges un BROUILLON que le pharmacien relira et corrigera avant envoi.

Règles :
- Réponds dans la langue de la question (français, kiswahili ou anglais).
- Court et clair : 2 à 5 phrases, sans jargon, sans titres ni listes à puces.
- Ni diagnostic ni prescription. Ne donne pas de posologie chiffrée précise si elle dépend de l'âge, \
du poids ou d'une maladie : renvoie à la notice, à l'ordonnance ou au pharmacien en officine.
- Si la question évoque des symptômes inquiétants (fièvre élevée persistante, enfant de moins de 2 ans, \
grossesse, saignement, difficulté à respirer, douleur forte, réaction allergique), mets \
orienter_medecin à true et conseille de consulter un médecin rapidement.
- Si le médicament exige une ordonnance, rappelle-le.
- N'invente rien : si tu n'es pas sûr, dis que le pharmacien vérifiera en officine.
- Écris au nom du pharmacien, sans mentionner que tu es une IA."""

SCHEMA = {
    "type": "object",
    "properties": {
        "reponse": {"type": "string", "description": "Brouillon de réponse au patient."},
        "orienter_medecin": {"type": "boolean", "description": "Vrai si le patient doit consulter un médecin."},
    },
    "required": ["reponse", "orienter_medecin"],
    "additionalProperties": False,
}


class AssistantIndisponible(Exception):
    """Suggestion impossible (non configuré, réseau, refus) : le pharmacien répond lui-même."""


@dataclass
class Suggestion:
    reponse: str
    orienter_medecin: bool


def assistant_actif():
    return bool(settings.ASSISTANT_IA_CLE)


def _client():
    return anthropic.Anthropic(api_key=settings.ASSISTANT_IA_CLE, timeout=60.0, max_retries=2)


def _contexte(question):
    m = question.medicament
    if m is None:
        return "Médicament concerné : non précisé."
    return (
        f"Médicament concerné : {m.nom_commercial} {m.dosage} ({m.get_forme_display()}), "
        f"DCI : {m.dci}, {'sur ordonnance' if m.ordonnance_requise else 'sans ordonnance'}."
    )


def suggerer_reponse(question):
    if not assistant_actif():
        raise AssistantIndisponible("Assistant IA non configuré.")
    try:
        resultat = _client().beta.messages.create(
            model=settings.ASSISTANT_IA_MODELE,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=CONSIGNES,
            messages=[{"role": "user", "content": f"{_contexte(question)}\n\nQuestion du patient :\n{question.texte}"}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except anthropic.APIStatusError as e:
        journal.warning("Assistant IA : erreur API %s", e.status_code)
        raise AssistantIndisponible("Le service IA a renvoyé une erreur.") from e
    except anthropic.APIConnectionError as e:
        journal.warning("Assistant IA : connexion impossible")
        raise AssistantIndisponible("Service IA injoignable.") from e

    if resultat.stop_reason == "refusal":
        raise AssistantIndisponible("L'IA n'a pas proposé de réponse pour cette question.")
    if resultat.stop_reason == "max_tokens":
        raise AssistantIndisponible("Réponse IA incomplète.")
    texte = next((b.text for b in resultat.content if b.type == "text"), "")
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as e:
        raise AssistantIndisponible("Réponse IA illisible.") from e
    return Suggestion(reponse=donnees["reponse"].strip()[:2000], orienter_medecin=bool(donnees["orienter_medecin"]))
