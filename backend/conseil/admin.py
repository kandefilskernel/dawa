from django.contrib import admin

from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["cree_le", "texte", "medicament", "statut", "repondu_par"]
    list_filter = ["statut", "cree_le"]
    search_fields = ["texte", "reponse"]
    readonly_fields = ["client_id", "cree_le", "repondu_le"]
