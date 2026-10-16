from django.contrib import admin

from .models import AppareilPush


@admin.register(AppareilPush)
class AppareilPushAdmin(admin.ModelAdmin):
    list_display = ["client_id", "langue", "maj_le"]
    list_filter = ["langue"]
    search_fields = ["client_id"]
    readonly_fields = ["client_id", "jeton", "maj_le"]
