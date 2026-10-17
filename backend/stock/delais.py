"""
Délai pour obtenir un médicament dans chaque pharmacie : trajet par la route + attente de l'ouverture.

Une pharmacie de garde est considérée ouverte. Un stock non confirmé récemment risque d'être faux
(déplacement pour rien) : il est classé comme s'il était un peu plus loin, sans changer le délai affiché.
"""
from pharmacies.horaires import etat
from pharmacies.trajets import MODES, trajets

PENALITE_STOCK_NON_CONFIRME_MIN = 15


def acces_pharmacie(pharmacie, trajets_pharmacie, de_garde, moment=None):
    if de_garde:
        ouverte, ouvre_dans = True, 0
    else:
        ouverte, ouvre_dans = etat(pharmacie.horaires, moment)
    attente = ouvre_dans if ouverte is False else 0
    return {
        "ouverte": ouverte,
        "ouvre_dans_min": ouvre_dans if ouverte is False else None,
        "trajets": {mode: t.en_dict() for mode, t in trajets_pharmacie.items()},
        # None : fermée sans ouverture connue dans la semaine.
        "delai_min": {
            mode: (t.minutes + attente) if attente is not None else None
            for mode, t in trajets_pharmacie.items()
        },
    }


def score(resultat, mode):
    delai = resultat.acces["delai_min"][mode]
    if delai is None:
        return float("inf")
    return delai + (0 if resultat.est_confirme else PENALITE_STOCK_NON_CONFIRME_MIN)


def classer_par_delai(resultats, depart, mode, ids_garde, moment=None):
    """Ajoute `acces` à chaque résultat (Stock) et trie du plus rapide au plus lent, puis par prix."""
    assert mode in MODES
    pharmacies = {r.pharmacie_id: r.pharmacie for r in resultats}
    ids = list(pharmacies)
    calcules = trajets(depart, [(pharmacies[i].position.y, pharmacies[i].position.x) for i in ids])
    acces = {
        i: acces_pharmacie(pharmacies[i], t, i in ids_garde, moment) for i, t in zip(ids, calcules)
    }
    for r in resultats:
        r.acces = acces[r.pharmacie_id]
    return sorted(resultats, key=lambda r: (score(r, mode), r.prix if r.prix is not None else 1 << 40))
