from django.http import FileResponse, Http404

from gestion.views import equipe_requise

from .models import Piece


@equipe_requise
def telecharger_piece(request, pk):
    """Pièce justificative : visible uniquement par l'équipe Uzima (stockage privé, hors /media/)."""
    piece = Piece.objects.filter(pk=pk).first()
    if piece is None or not piece.fichier.storage.exists(piece.fichier.name):
        raise Http404
    reponse = FileResponse(piece.fichier.open("rb"), filename=piece.nom_original or piece.fichier.name,
                           as_attachment=False)
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = "private, no-store"
    reponse["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"
    return reponse
