import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../langue.dart';
import '../ecrans/fiche_pharmacie.dart';
import '../ecrans/itineraire.dart';
import '../models.dart';
import '../theme.dart';
import 'communs.dart';
import 'reservation_sheet.dart';
import 'trajet.dart';
import 'image_medicament.dart';

String formatPrix(int prix) {
  final chiffres = prix.toString();
  final groupes = <String>[];
  for (var fin = chiffres.length; fin > 0; fin -= 3) {
    groupes.insert(0, chiffres.substring(fin - 3 < 0 ? 0 : fin - 3, fin));
  }
  return '${groupes.join(' ')} FC';
}

String formatDistance(double km) =>
    km < 1 ? '${(km * 1000).round()} m' : '${km.toStringAsFixed(1).replaceAll('.', ',')} km';

Future<void> _ouvrir(BuildContext context, Uri uri, String echec) async {
  final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(echec)));
  }
}

Future<void> appeler(BuildContext context, String telephone) =>
    _ouvrir(context, Uri(scheme: 'tel', path: telephone), tr('Impossible d\'appeler {telephone}', {'telephone': telephone}));

/// Trajet tracé sur la carte de l'app, avec distance et durée.
Future<void> itineraire(BuildContext context, double lat, double lng, {required String nom}) =>
    ouvrirItineraire(context, nom: nom, lat: lat, lng: lng);

/// Itinéraire dans Google Maps (navigation guidée).
Future<void> itineraireExterne(BuildContext context, double lat, double lng) => _ouvrir(
      context,
      Uri.https('www.google.com', '/maps/dir/', {'api': '1', 'destination': '$lat,$lng'}),
      tr('Impossible d\'ouvrir la carte'),
    );

/// Fiche d'une pharmacie, avec éventuellement le produit et le prix trouvés.
class PharmacieCarte extends StatelessWidget {
  const PharmacieCarte({
    super.key,
    required this.pharmacie,
    this.resultat,
    this.medicamentRecherche,
    this.meilleurPrix = false,
    this.plusProche = false,
    this.plusRapide = false,
    this.mode = ModeTrajet.moto,
  });

  final Pharmacie pharmacie;
  final Resultat? resultat;
  final Medicament? medicamentRecherche;
  final bool meilleurPrix;
  final bool plusProche;
  final bool plusRapide;

  /// Mode de trajet pour le délai affiché (résultats de recherche avec position).
  final ModeTrajet mode;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final r = resultat;
    final acces = r?.acces;
    // Avec un trajet calculé, la distance par la route est affichée plus bas.
    final distance = acces != null ? null : r?.distanceKm ?? pharmacie.distanceKm;
    final equivalent = r != null && medicamentRecherche != null && r.medicament.id != medicamentRecherche!.id;

    final pastilles = [
      if (meilleurPrix) Pastille(tr('Meilleur prix'), couleur: Couleurs.ambreFonce, icone: Icons.sell, plein: true),
      if (plusRapide) Pastille(tr('Le plus rapide'), couleur: Couleurs.emeraude, icone: Icons.bolt, plein: true),
      if (plusProche) Pastille(tr('Le plus proche'), couleur: Couleurs.emeraude, icone: Icons.near_me, plein: true),
      if (pharmacie.deGarde) Pastille(tr('De garde'), couleur: Couleurs.indigo, icone: Icons.nightlight_round),
      if (r != null && !r.confirme)
        Pastille(tr('Stock à confirmer'), couleur: Color(0xFFB45309), icone: Icons.schedule),
    ];

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => ouvrirFichePharmacie(context, pharmacie),
        child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (pastilles.isNotEmpty) ...[
            Wrap(spacing: 6, runSpacing: 6, children: pastilles),
            const SizedBox(height: 12),
          ],
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                gradient: pharmacie.deGarde ? Couleurs.degradeNuit : Couleurs.degradeMarque,
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.local_pharmacy, color: Colors.white, size: 26),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(pharmacie.nom, style: theme.textTheme.titleMedium),
                const SizedBox(height: 4),
                Row(children: [
                  if (distance != null) ...[
                    const Icon(Icons.place_outlined, size: 15, color: Couleurs.texteDoux),
                    const SizedBox(width: 2),
                    Text(formatDistance(distance), style: theme.textTheme.bodySmall),
                    const SizedBox(width: 10),
                  ],
                  if (pharmacie.quartier.isNotEmpty)
                    Flexible(
                      child: Text(pharmacie.quartier,
                          style: theme.textTheme.bodySmall, overflow: TextOverflow.ellipsis),
                    ),
                ]),
                if (r == null && pharmacie.horaires.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Row(children: [
                    const Icon(Icons.schedule, size: 14, color: Couleurs.texteDoux),
                    const SizedBox(width: 4),
                    Text(pharmacie.horaires, style: theme.textTheme.bodySmall),
                  ]),
                ],
              ]),
            ),
            if (r?.prix != null) ...[
              const SizedBox(width: 8),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(formatPrix(r!.prix!).replaceAll(' FC', ''),
                    style: theme.textTheme.titleLarge?.copyWith(
                        color: Couleurs.emeraudeFonce, fontWeight: FontWeight.w800)),
                Text('FC', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700)),
              ]),
            ],
          ]),
          if (acces != null) ...[
            const SizedBox(height: 12),
            LigneAcces(acces: acces, mode: mode),
          ],
          if (r != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(color: Couleurs.fond, borderRadius: BorderRadius.circular(12)),
              child: Row(children: [
                ImageMedicament(r.medicament, taille: 36, rayon: 9),
                const SizedBox(width: 10),
                Expanded(
                  child: Text.rich(TextSpan(children: [
                    if (equivalent)
                      TextSpan(text: tr('Équivalent : '), style: TextStyle(color: Couleurs.texteDoux)),
                    TextSpan(text: r.medicament.libelle, style: const TextStyle(fontWeight: FontWeight.w600)),
                  ])),
                ),
                const Icon(Icons.check_circle, size: 18, color: Couleurs.emeraude),
                const SizedBox(width: 4),
                Text(tr('En stock'),
                    style: TextStyle(color: Couleurs.emeraudeFonce, fontWeight: FontWeight.w700, fontSize: 13)),
              ]),
            ),
          ],
          const SizedBox(height: 12),
          _Actions(pharmacie: pharmacie, resultat: r),
        ]),
        ),
      ),
    );
  }
}

class _Actions extends StatelessWidget {
  const _Actions({required this.pharmacie, this.resultat});

  final Pharmacie pharmacie;
  final Resultat? resultat;

  @override
  Widget build(BuildContext context) {
    final r = resultat;
    final boutonItineraire = Tooltip(
      message: tr('Itinéraire'),
      child: OutlinedButton(
        onPressed: () => itineraire(context, pharmacie.lat, pharmacie.lng, nom: pharmacie.nom),
        style: OutlinedButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(52, 48)),
        child: Icon(Icons.directions_outlined, size: 22, semanticLabel: tr('Itinéraire')),
      ),
    );
    if (r == null) {
      return Row(children: [
        Expanded(
          child: FilledButton.icon(
            onPressed: () => appeler(context, pharmacie.telephone),
            icon: const Icon(Icons.call, size: 18),
            label: Text(tr('Appeler')),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: OutlinedButton.icon(
            onPressed: () => itineraire(context, pharmacie.lat, pharmacie.lng, nom: pharmacie.nom),
            icon: const Icon(Icons.directions_outlined, size: 18),
            label: Text(tr('Itinéraire')),
          ),
        ),
      ]);
    }
    return Row(children: [
      Expanded(
        child: FilledButton.icon(
          onPressed: () => ouvrirReservation(context, pharmacie: pharmacie, medicament: r.medicament, prix: r.prix),
          icon: const Icon(Icons.shopping_bag_outlined, size: 18),
          label: Text(tr('Réserver')),
        ),
      ),
      const SizedBox(width: 8),
      Tooltip(
        message: tr('Appeler'),
        child: OutlinedButton(
          onPressed: () => appeler(context, pharmacie.telephone),
          style: OutlinedButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(52, 48)),
          child: Icon(Icons.call_outlined, size: 22, semanticLabel: tr('Appeler la pharmacie')),
        ),
      ),
      const SizedBox(width: 8),
      boutonItineraire,
    ]);
  }
}
