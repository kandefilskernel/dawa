import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../langue.dart';
import '../models.dart';
import '../position.dart';
import '../theme.dart';
import 'pharmacie_carte.dart';

/// Carte OpenStreetMap : position de l'utilisateur et étiquettes de prix des pharmacies.
class CartePharmacies extends StatelessWidget {
  const CartePharmacies({
    super.key,
    required this.position,
    required this.resultats,
    this.medicamentRecherche,
    this.mode = ModeTrajet.moto,
  });

  final Position position;
  final List<Resultat> resultats;
  final Medicament? medicamentRecherche;
  final ModeTrajet mode;

  @override
  Widget build(BuildContext context) {
    // Une pharmacie peut avoir plusieurs produits équivalents : on garde le moins cher.
    final parPharmacie = <int, Resultat>{};
    for (final r in resultats) {
      final actuel = parPharmacie[r.pharmacie.id];
      if (actuel == null || (r.prix ?? 1 << 30) < (actuel.prix ?? 1 << 30)) {
        parPharmacie[r.pharmacie.id] = r;
      }
    }

    return FlutterMap(
      options: MapOptions(initialCenter: LatLng(position.lat, position.lng), initialZoom: 13.5),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'cd.dawa.dawa',
        ),
        MarkerLayer(markers: [
          Marker(
            point: LatLng(position.lat, position.lng),
            width: 44,
            height: 44,
            child: Container(
              decoration: BoxDecoration(
                color: Colors.blue.withValues(alpha: 0.18),
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: Colors.blue,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: ombreDouce,
                ),
              ),
            ),
          ),
          for (final r in parPharmacie.values)
            Marker(
              point: LatLng(r.pharmacie.lat, r.pharmacie.lng),
              width: 96,
              height: 46,
              alignment: Alignment.topCenter,
              child: GestureDetector(
                onTap: () => _details(context, r),
                child: _EtiquettePrix(resultat: r),
              ),
            ),
        ]),
        RichAttributionWidget(attributions: [
          TextSourceAttribution(tr('© contributeurs OpenStreetMap')),
        ]),
      ],
    );
  }

  void _details(BuildContext context, Resultat resultat) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: PharmacieCarte(
            pharmacie: resultat.pharmacie,
            resultat: resultat,
            medicamentRecherche: medicamentRecherche,
            mode: mode,
          ),
        ),
      ),
    );
  }
}

class _EtiquettePrix extends StatelessWidget {
  const _EtiquettePrix({required this.resultat});

  final Resultat resultat;

  @override
  Widget build(BuildContext context) {
    final couleur = resultat.pharmacie.deGarde ? Couleurs.indigo : Couleurs.emeraude;
    final prix = resultat.prix;
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Container(
        padding: const EdgeInsets.fromLTRB(6, 5, 10, 5),
        decoration: BoxDecoration(
          color: couleur,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white, width: 2),
          boxShadow: ombreDouce,
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.local_pharmacy, size: 16, color: Colors.white),
          const SizedBox(width: 4),
          Text(
            prix != null ? formatPrix(prix) : tr('En stock'),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12),
          ),
        ]),
      ),
      CustomPaint(size: const Size(12, 7), painter: _Pointe(couleur)),
    ]);
  }
}

class _Pointe extends CustomPainter {
  _Pointe(this.couleur);

  final Color couleur;

  @override
  void paint(Canvas canvas, Size size) {
    final chemin = ui.Path()
      ..moveTo(0, 0)
      ..lineTo(size.width, 0)
      ..lineTo(size.width / 2, size.height)
      ..close();
    canvas.drawPath(chemin, Paint()..color = couleur);
  }

  @override
  bool shouldRepaint(_Pointe ancien) => ancien.couleur != couleur;
}
