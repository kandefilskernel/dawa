"""Données de démonstration : pharmacies FICTIVES à Lubumbashi et médicaments courants."""

import os
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Garde, Pharmacie
from portail.models import Pharmacien
from verification.models import Lot
from sante.models import Etablissement
from stock.models import Stock

# (DCI, nom commercial, dosage, forme, ordonnance requise, prix indicatif en FC)
MEDICAMENTS = [
    ("Paracétamol", "Paracétamol", "500 mg", "comprime", False, 1500),
    ("Paracétamol", "Doliprane", "500 mg", "comprime", False, 4500),
    ("Paracétamol", "Panadol", "500 mg", "comprime", False, 4000),
    ("Paracétamol", "Paracétamol sirop", "120 mg/5 ml", "sirop", False, 3500),
    ("Ibuprofène", "Ibuprofène", "400 mg", "comprime", False, 2500),
    ("Amoxicilline", "Amoxicilline", "500 mg", "gelule", True, 5000),
    ("Amoxicilline", "Amoxicilline suspension", "250 mg/5 ml", "suspension", True, 6000),
    ("Amoxicilline + acide clavulanique", "Augmentin", "1 g", "comprime", True, 25000),
    ("Artéméther + luméfantrine", "Coartem", "20/120 mg", "comprime", False, 12000),
    ("Artéméther + luméfantrine", "Lumartem", "20/120 mg", "comprime", False, 8000),
    ("Artésunate + amodiaquine", "ASAQ", "100/270 mg", "comprime", False, 7000),
    ("Quinine", "Quinine", "300 mg", "comprime", True, 6000),
    ("Quinine", "Quinine injectable", "600 mg/2 ml", "injectable", True, 4000),
    ("Métronidazole", "Flagyl", "500 mg", "comprime", True, 5000),
    ("Ciprofloxacine", "Ciprofloxacine", "500 mg", "comprime", True, 7000),
    ("Cotrimoxazole", "Cotrimoxazole", "480 mg", "comprime", True, 3000),
    ("Sels de réhydratation orale", "SRO", "20,5 g", "sachet", False, 1000),
    ("Zinc", "Zinc", "20 mg", "comprime", False, 2000),
    ("Oméprazole", "Oméprazole", "20 mg", "gelule", False, 4000),
    ("Mébendazole", "Vermox", "500 mg", "comprime", False, 3000),
    ("Albendazole", "Albendazole", "400 mg", "comprime", False, 2000),
    ("Amlodipine", "Amlodipine", "5 mg", "comprime", True, 6000),
    ("Metformine", "Metformine", "500 mg", "comprime", True, 5000),
    ("Salbutamol", "Ventoline", "100 µg/dose", "autre", True, 15000),
    ("Fer + acide folique", "Fer-Folate", "200/0,4 mg", "comprime", False, 2500),
    ("Diclofénac", "Diclofénac", "50 mg", "comprime", False, 2500),
    ("Chlorphénamine", "Chlorphénamine", "4 mg", "comprime", False, 1500),
    ("Vitamine C", "Vitamine C", "500 mg", "comprime", False, 2000),
]

# Pharmacies fictives, positions approximatives dans les communes de Lubumbashi.
PHARMACIES = [
    ("Pharmacie Démo Centre", "Av. Mama Yemo", "Centre-ville", "Lubumbashi", -11.664, 27.479),
    ("Pharmacie Démo Kenya", "Av. du Marché", "Kenya", "Kenya", -11.688, 27.468),
    ("Pharmacie Démo Kamalondo", "Av. Kasaï", "Kamalondo", "Kamalondo", -11.677, 27.484),
    ("Pharmacie Démo Kampemba", "Av. Kasapa", "Bel-Air", "Kampemba", -11.655, 27.502),
    ("Pharmacie Démo Ruashi", "Route Ruashi", "Ruashi", "Ruashi", -11.625, 27.528),
    ("Pharmacie Démo Katuba", "Av. Katuba", "Katuba", "Katuba", -11.703, 27.451),
    ("Pharmacie Démo Golf", "Av. des Chutes", "Golf", "Lubumbashi", -11.652, 27.467),
    ("Pharmacie Démo Annexe", "Route Kasumbalesa", "Annexe", "Annexe", -11.610, 27.430),
    ("Pharmacie Démo Bel-Air", "Av. Bel-Air", "Bel-Air", "Kampemba", -11.660, 27.512),
    ("Pharmacie Démo Gambela", "Av. Lumumba", "Gambela", "Lubumbashi", -11.672, 27.492),
]

# Établissements de santé FICTIFS : (nom, type, quartier, lat, lng, urgences 24h, services)
ETABLISSEMENTS = [
    ("Hôpital Démo Central", "hopital", "Centre-ville", -11.668, 27.474, True, "Urgences, chirurgie, pédiatrie, maternité"),
    ("Clinique Démo du Golf", "clinique", "Golf", -11.650, 27.462, True, "Médecine générale, radiologie"),
    ("Centre de santé Démo Kenya", "centre_sante", "Kenya", -11.690, 27.472, False, "Consultations, vaccination, CPN"),
    ("Centre de santé Démo Ruashi", "centre_sante", "Ruashi", -11.628, 27.524, False, "Consultations, paludisme, vaccination"),
    ("Laboratoire Démo Analyses", "laboratoire", "Centre-ville", -11.661, 27.483, False, "Analyses sanguines, goutte épaisse, glycémie"),
    ("Maternité Démo Kampemba", "maternite", "Bel-Air", -11.657, 27.506, True, "Accouchements, suivi de grossesse"),
]

# Lots FICTIFS pour essayer la vérification : (nom commercial, numéro, statut, expiration)
LOTS_DEMO = [
    ("Coartem", "DEMO-C001", "conforme", "2027-06-30"),
    ("Coartem", "DEMO-C666", "contrefait", None),
    ("Amoxicilline", "DEMO-A777", "rappele", "2026-12-31"),
    ("Doliprane", "DEMO-D100", "conforme", "2025-12-31"),
    ("Doliprane", "DEMO-D200", "conforme", "2028-01-31"),
]


def code_barres_interne(numero):
    """EAN-13 au préfixe 200 (usage interne, jamais attribué à un vrai produit), clé de contrôle comprise."""
    base = f"200{numero:09d}"
    somme = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(base))
    return base + str((10 - somme % 10) % 10)


class Command(BaseCommand):
    help = "Remplit la base avec des données de démonstration (fictives)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Efface d'abord les données.")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        rng = random.Random(42)
        if reset:
            Stock.objects.all().delete()
            Garde.objects.all().delete()
            Pharmacie.objects.all().delete()
            Medicament.objects.all().delete()
            Etablissement.objects.all().delete()

        medicaments = []
        prix_indicatif = {}
        for dci, nom, dosage, forme, ordonnance, prix in MEDICAMENTS:
            med, _ = Medicament.objects.update_or_create(
                nom_commercial=nom, dosage=dosage, forme=forme,
                defaults={"dci": dci, "ordonnance_requise": ordonnance},
            )
            if not med.code_barres:
                med.code_barres = code_barres_interne(med.id)
                med.save(update_fields=["code_barres"])
            medicaments.append(med)
            prix_indicatif[med.id] = prix

        pharmacies = []
        for i, (nom, adresse, quartier, commune, lat, lng) in enumerate(PHARMACIES):
            pharmacie, _ = Pharmacie.objects.update_or_create(
                nom=nom,
                defaults={
                    "adresse": adresse, "quartier": quartier, "commune": commune,
                    "telephone": f"+24399000{i:04d}", "horaires": "Lun–Sam 8h–20h",
                    "position": Point(lng, lat, srid=4326), "est_validee": True,
                },
            )
            pharmacies.append(pharmacie)

        for pharmacie in pharmacies:
            for med in rng.sample(medicaments, k=rng.randint(12, 22)):
                variation = rng.choice([0.9, 1.0, 1.0, 1.1, 1.2])
                Stock.objects.update_or_create(
                    pharmacie=pharmacie, medicament=med,
                    defaults={
                        "disponible": rng.random() > 0.15,
                        "prix": int(round(prix_indicatif[med.id] * variation, -2)),
                        "source": Stock.Source.ADMIN,
                    },
                )

        # Deux pharmacies de garde, de maintenant à demain 8h.
        maintenant = timezone.localtime()
        fin = (maintenant + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        Garde.objects.filter(debut__lte=maintenant, fin__gt=maintenant).delete()
        for pharmacie in rng.sample(pharmacies, k=2):
            Garde.objects.create(pharmacie=pharmacie, debut=maintenant, fin=fin)

        for i, (nom, type_, quartier, lat, lng, urgences, services) in enumerate(ETABLISSEMENTS):
            Etablissement.objects.update_or_create(
                nom=nom,
                defaults={
                    "type": type_, "adresse": f"Av. Démo {i + 1}", "quartier": quartier,
                    "telephone": f"+24397000{i:04d}", "position": Point(lng, lat, srid=4326),
                    "urgences_24h": urgences, "services": services, "est_valide": True,
                },
            )

        # Compte portail de démonstration pour la première pharmacie (mot de passe dans .env).
        mot_de_passe = os.environ.get("DAWA_DEMO_MOT_DE_PASSE")
        if mot_de_passe:
            utilisateur, _ = get_user_model().objects.get_or_create(username="pharmacie-centre")
            utilisateur.set_password(mot_de_passe)
            utilisateur.save()
            Pharmacien.objects.update_or_create(utilisateur=utilisateur, defaults={"pharmacie": pharmacies[0]})
            self.stdout.write(f"Compte portail « pharmacie-centre » → {pharmacies[0].nom}")
            # Compte équipe pour l'espace Dawa (/dawa/) : validations, visibilité, abonnements.
            equipe, _ = get_user_model().objects.get_or_create(username="equipe-dawa")
            equipe.is_staff = True
            equipe.set_password(mot_de_passe)
            equipe.save()
            self.stdout.write("Compte équipe « equipe-dawa » → /dawa/")

        for nom, numero, statut, expiration in LOTS_DEMO:
            medicament = Medicament.objects.filter(nom_commercial=nom).first()
            if medicament:
                Lot.objects.update_or_create(
                    medicament=medicament, numero=numero,
                    defaults={"statut": statut, "date_expiration": expiration,
                              "fabricant": "Fabricant démo", "source": "Données de démonstration"},
                )

        call_command("generer_images", stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS(
            f"{len(medicaments)} médicaments, {len(pharmacies)} pharmacies, "
            f"{Stock.objects.count()} lignes de stock, {len(ETABLISSEMENTS)} établissements de santé."
        ))
