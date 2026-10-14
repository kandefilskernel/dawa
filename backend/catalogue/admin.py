from django.contrib import admin
from django.utils.html import format_html

from .images import nom_fichier, preparer_photo
from .models import Medicament


def _vignette(obj, taille):
    if not obj.image:
        return "—"
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:8px">',
                       obj.image.url, taille, taille)


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ["miniature", "nom_commercial", "dci", "dosage", "forme", "ordonnance_requise", "image_est_illustration"]
    list_display_links = ["miniature", "nom_commercial"]
    list_filter = ["forme", "ordonnance_requise", "image_est_illustration", "image_envoyee_par"]
    search_fields = ["nom_commercial", "dci", "code_barres"]
    readonly_fields = ["apercu"]
    fields = ["dci", "nom_commercial", "dosage", "forme", "code_barres", "ordonnance_requise",
              "image", "apercu", "image_est_illustration", "image_envoyee_par", "image_credit"]

    @admin.display(description="image")
    def miniature(self, obj):
        return _vignette(obj, 44)

    @admin.display(description="aperçu")
    def apercu(self, obj):
        return _vignette(obj, 220)

    def save_model(self, request, obj, form, change):
        # Une photo envoyée est compressée (WebP ≤ 800 px) et remplace l'illustration générée.
        if "image" in form.changed_data and obj.image:
            obj.image = preparer_photo(obj.image, nom_fichier(obj))
            obj.image_est_illustration = False
            obj.image_envoyee_par = None  # Photo validée par l'équipe Dawa.
            if "image_credit" not in form.changed_data:
                obj.image_credit = ""  # Le crédit de l'ancienne photo ne vaut pas pour la nouvelle.
        super().save_model(request, obj, form, change)
