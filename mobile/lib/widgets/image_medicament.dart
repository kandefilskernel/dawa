import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../langue.dart';
import '../config.dart';
import '../models.dart';
import '../theme.dart';
import 'communs.dart';

/// Image d'un médicament, mise en cache sur le téléphone (téléchargée une seule fois).
/// Repli sur l'icône de la forme si l'image manque ou ne charge pas (hors ligne).
class ImageMedicament extends StatelessWidget {
  const ImageMedicament(this.medicament, {super.key, this.taille = 44, this.rayon});

  final Medicament medicament;
  final double taille;
  final double? rayon;

  static String? urlAbsolue(String? url) {
    if (url == null || url.isEmpty) return null;
    return url.startsWith('http') ? url : '$apiUrl$url';
  }

  @override
  Widget build(BuildContext context) {
    final url = urlAbsolue(medicament.image);
    final repli = IconeTeintee(iconeForme(medicament.formeLibelle), taille: taille);
    if (url == null) return repli;

    final pixels = (taille * MediaQuery.devicePixelRatioOf(context)).round();
    return ClipRRect(
      borderRadius: BorderRadius.circular(rayon ?? taille * 0.28),
      child: CachedNetworkImage(
        imageUrl: url,
        width: taille,
        height: taille,
        fit: BoxFit.cover,
        // Décode à la taille affichée : moins de mémoire sur les téléphones d'entrée de gamme.
        memCacheWidth: pixels,
        fadeInDuration: const Duration(milliseconds: 150),
        placeholder: (_, _) => Container(
          width: taille,
          height: taille,
          color: Couleurs.menthe.withValues(alpha: 0.5),
        ),
        errorWidget: (_, _, _) => repli,
      ),
    );
  }
}

/// Affiche l'image en grand (fiche produit), avec la mention « illustration » ou le crédit
/// de la photo (auteur et licence, exigés par CC BY / CC BY-SA) si besoin.
void ouvrirImageMedicament(BuildContext context, Medicament medicament) {
  final url = ImageMedicament.urlAbsolue(medicament.image);
  if (url == null) return;
  showDialog(
    context: context,
    builder: (_) => Dialog(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      // Largeur limitée et défilement : en paysage, l'image carrée ne cache plus le texte (crédit).
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            AspectRatio(aspectRatio: 1, child: CachedNetworkImage(imageUrl: url, fit: BoxFit.cover)),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(medicament.libelle, style: Theme.of(context).textTheme.titleMedium),
                Text([medicament.dci, tr(medicament.formeLibelle)].where((s) => s.isNotEmpty).join(' · '),
                    style: Theme.of(context).textTheme.bodySmall),
                if (medicament.imageEstIllustration) ...[
                  const SizedBox(height: 8),
                  Text(tr('Image d\'illustration : la boîte vendue peut être différente.'),
                      style: TextStyle(fontSize: 12, color: Couleurs.texteDoux, fontStyle: FontStyle.italic)),
                ],
                if (medicament.imageCredit.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SelectableText(medicament.imageCredit,
                      style: TextStyle(fontSize: 11, color: Couleurs.texteDoux)),
                ],
              ]),
            ),
          ]),
        ),
      ),
    ),
  );
}
