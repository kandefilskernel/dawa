"""Dossier KYC d'une structure : pièces demandées, dernière pièce envoyée par type, état du dossier."""
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from django import forms

from .models import Piece, nom_fichier_piece

# Pièces demandées à toute structure (à ajuster avec l'Inspection provinciale de la santé).
OBLIGATOIRES = [Piece.Type.AUTORISATION, Piece.Type.ORDRE, Piece.Type.IDENTITE, Piece.Type.FACADE]
FACULTATIVES = [Piece.Type.RCCM, Piece.Type.ID_NAT]

AIDES = {
    Piece.Type.AUTORISATION: "Document officiel autorisant l'ouverture ou l'exploitation de la structure.",
    Piece.Type.ORDRE: "Carte de membre de l'Ordre du pharmacien titulaire ou du médecin directeur.",
    Piece.Type.IDENTITE: "Carte d'électeur, passeport ou permis du responsable.",
    Piece.Type.FACADE: "Photo prise devant la structure, enseigne lisible.",
}

EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
TAILLE_MAX = 8 * 1024 * 1024


@dataclass
class Ligne:
    type: str
    libelle: str
    aide: str
    obligatoire: bool
    piece: Piece | None


class Dossier:
    def __init__(self, pieces):
        self.dernieres = {}
        for piece in sorted(pieces, key=lambda p: p.envoyee_le, reverse=True):
            self.dernieres.setdefault(piece.type, piece)

    @property
    def lignes(self):
        return [
            Ligne(t, Piece.Type(t).label, AIDES.get(t, ""), t in OBLIGATOIRES, self.dernieres.get(t))
            for t in OBLIGATOIRES + FACULTATIVES
        ]

    @property
    def manquantes(self):
        """Pièces obligatoires absentes ou rejetées : à (r)envoyer par la structure."""
        return [t for t in OBLIGATOIRES
                if t not in self.dernieres or self.dernieres[t].statut == Piece.Statut.REJETEE]

    @property
    def a_verifier(self):
        return [p for p in self.dernieres.values() if p.statut == Piece.Statut.EN_ATTENTE]

    @property
    def verifie(self):
        """Toutes les pièces obligatoires acceptées : la structure peut être validée."""
        return all(t in self.dernieres and self.dernieres[t].statut == Piece.Statut.ACCEPTEE for t in OBLIGATOIRES)


class PieceForm(forms.Form):
    type = forms.ChoiceField(choices=Piece.Type.choices)
    fichier = forms.FileField(label="Fichier (PDF ou photo)")

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        nom = fichier.name.lower()
        if not any(nom.endswith(ext) for ext in EXTENSIONS):
            raise forms.ValidationError("Formats acceptés : PDF, JPG, PNG ou WebP.")
        if fichier.size > TAILLE_MAX:
            raise forms.ValidationError("Fichier trop lourd (8 Mo maximum).")
        # Vérifie le contenu réel, pas seulement l'extension.
        if nom.endswith(".pdf"):
            if fichier.read(5) != b"%PDF-":
                raise forms.ValidationError("Ce fichier n'est pas un PDF valide.")
        else:
            try:
                Image.open(fichier).verify()
            except (UnidentifiedImageError, OSError, SyntaxError):
                raise forms.ValidationError("Cette image est illisible.")
        fichier.seek(0)
        return fichier

    def enregistrer(self, **structure):
        fichier = self.cleaned_data["fichier"]
        piece = Piece(type=self.cleaned_data["type"], nom_original=fichier.name[:150], **structure)
        piece.fichier.save(nom_fichier_piece(fichier.name), fichier, save=False)
        piece.save()
        return piece
