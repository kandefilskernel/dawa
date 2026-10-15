"""Espace web des établissements de santé : inscription, justificatifs (KYC) et fiche affichée dans l'app."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from kyc.dossier import Dossier, PieceForm

from .forms import FicheEtablissementForm, InscriptionEtablissementForm


def inscription(request):
    if request.user.is_authenticated:
        return redirect("etablissement:espace")
    formulaire = InscriptionEtablissementForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        responsable = formulaire.save()
        login(request, responsable.utilisateur, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("etablissement:espace")
    return render(request, "sante/inscription.html", {"form": formulaire})


@login_required
def espace(request):
    responsable = getattr(request.user, "responsable_etablissement", None)
    if responsable is None:
        return redirect("portail:tableau")
    etablissement = responsable.etablissement
    form_piece = fiche = None
    if request.method == "POST" and request.POST.get("formulaire") == "piece":
        form_piece = PieceForm(request.POST, request.FILES)
        if form_piece.is_valid():
            form_piece.enregistrer(etablissement=etablissement)
            messages.success(request, "Document envoyé. L'équipe Dawa va le vérifier.")
            return redirect("etablissement:espace")
        messages.error(request, " ".join(e for erreurs in form_piece.errors.values() for e in erreurs))
    elif request.method == "POST" and responsable.actif:
        fiche = FicheEtablissementForm(request.POST, instance=etablissement)
        if fiche.is_valid():
            fiche.save()
            messages.success(request, "Fiche mise à jour.")
            return redirect("etablissement:espace")
    return render(request, "sante/espace.html", {
        "responsable": responsable,
        "etablissement": etablissement,
        "dossier": Dossier(etablissement.pieces.all()),
        "action": reverse("etablissement:espace"),
        "fiche": fiche or (FicheEtablissementForm(instance=etablissement) if responsable.actif else None),
    }, status=200 if responsable.actif else 403)
