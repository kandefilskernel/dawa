"""
Lecture des horaires saisis librement par les pharmacies (« Lun–Sam 8h–20h, Dim 9h–13h »).

Sert à savoir si une pharmacie est ouverte maintenant et, sinon, dans combien de temps elle ouvre.
Un texte illisible ou vide donne « inconnu » : on ne pénalise pas la pharmacie pour autant.
"""
import re
from datetime import timedelta

from django.utils import timezone

JOURS = {"lun": 0, "mar": 1, "mer": 2, "jeu": 3, "ven": 4, "sam": 5, "dim": 6}
_JOUR = r"(lun|mar|mer|jeu|ven|sam|dim)[a-z]*\.?"
_HEURE = r"(\d{1,2})\s*(?:h|:)\s*(\d{2})?"
_TIRET = r"\s*(?:-|–|—|à|a)\s*"
_BLOC = re.compile(rf"{_JOUR}(?:{_TIRET}{_JOUR})?\s*:?\s*{_HEURE}{_TIRET}{_HEURE}")
_TOUS_LES_JOURS = re.compile(rf"(?:tous les jours|7\s*j\s*/\s*7)\s*:?\s*{_HEURE}{_TIRET}{_HEURE}")


def maintenant():
    return timezone.localtime()


def _minutes(heures, minutes):
    return int(heures) * 60 + int(minutes or 0)


def plages(horaires):
    """{jour (0 = lundi): [(début, fin) en minutes]} ou None si le texte est illisible."""
    texte = (horaires or "").lower().replace(" ", " ")
    if not texte.strip():
        return None
    if re.search(r"24\s*h?\s*/\s*24|24h sur 24", texte):
        return {jour: [(0, 24 * 60)] for jour in range(7)}
    resultat = {}
    for m in _TOUS_LES_JOURS.finditer(texte):
        for jour in range(7):
            resultat.setdefault(jour, []).append((_minutes(m[1], m[2]), _minutes(m[3], m[4])))
    for m in _BLOC.finditer(texte):
        premier, dernier = JOURS[m[1]], JOURS[m[2] or m[1]]
        plage = (_minutes(m[3], m[4]), _minutes(m[5], m[6]))
        jour = premier
        while True:
            resultat.setdefault(jour, []).append(plage)
            if jour == dernier:
                break
            jour = (jour + 1) % 7
    return resultat or None


def etat(horaires, moment=None):
    """
    (ouverte, ouvre_dans_minutes) au moment donné :
    (True, 0) ouverte ; (False, n) fermée, ouvre dans n minutes ; (None, None) horaires inconnus ;
    (False, None) fermée sans ouverture prévue dans la semaine.
    """
    p = plages(horaires)
    if p is None:
        return None, None
    moment = timezone.localtime(moment) if moment else maintenant()
    debut_jour = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    minute = moment.hour * 60 + moment.minute
    for decalage in range(8):
        jour = (moment.weekday() + decalage) % 7
        for debut, fin in sorted(p.get(jour, [])):
            if decalage == 0 and debut <= minute < (fin if fin > debut else 24 * 60):
                return True, 0
            ouverture = debut_jour + timedelta(days=decalage, minutes=debut)
            if ouverture > moment:
                return False, int((ouverture - moment).total_seconds() // 60)
    return False, None
