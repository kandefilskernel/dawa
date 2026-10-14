from django import forms

from pharmacies.models import Pharmacie


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Pharmacie
        fields = ["telephone", "whatsapp", "horaires", "adresse", "quartier"]
        labels = {
            "telephone": "Téléphone",
            "whatsapp": "WhatsApp",
            "horaires": "Horaires d'ouverture",
            "adresse": "Adresse",
            "quartier": "Quartier",
        }
        help_texts = {"horaires": "Ex. Lun–Sam 8h–20h, Dim 9h–13h"}
