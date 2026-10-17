import uuid

import django.contrib.gis.db.models.fields
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def jetons_livreurs(apps, schema_editor):
    Livreur = apps.get_model("reservations", "Livreur")
    for livreur in Livreur.objects.all():
        livreur.jeton = uuid.uuid4()
        livreur.save(update_fields=["jeton"])


class Migration(migrations.Migration):

    dependencies = [
        ("reservations", "0002_reservation_adresse_livraison_and_more"),
    ]

    operations = [
        # Un jeton différent par livreur existant, puis la contrainte d'unicité.
        migrations.AddField(
            model_name="livreur",
            name="jeton",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(jetons_livreurs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="livreur",
            name="jeton",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name="PositionLivreur",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("vitesse_kmh", models.FloatField(blank=True, help_text="Vitesse donnée par le GPS.", null=True)),
                ("precision_m", models.FloatField(blank=True, null=True)),
                ("recue_le", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="positions", to="reservations.reservation")),
            ],
            options={
                "verbose_name": "position du livreur",
                "verbose_name_plural": "positions des livreurs",
                "ordering": ["recue_le"],
            },
        ),
    ]
