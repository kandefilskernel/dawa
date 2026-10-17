import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../api.dart';
import '../langue.dart';
import '../models.dart';
import '../position.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import '../widgets/trajet.dart';

/// Ouvre le trajet jusqu'à une pharmacie (ou un établissement de santé) sur la carte de l'app.
Future<void> ouvrirItineraire(BuildContext context, {required String nom, required double lat, required double lng}) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => EcranItineraire(nom: nom, lat: lat, lng: lng)));

class EcranItineraire extends StatefulWidget {
  const EcranItineraire({super.key, required this.nom, required this.lat, required this.lng});

  final String nom;
  final double lat;
  final double lng;

  @override
  State<EcranItineraire> createState() => _EcranItineraireState();
}

class _EcranItineraireState extends State<EcranItineraire> {
  ModeTrajet _mode = stockage.modeTrajet;
  Position? _position;
  Itineraire? _itineraire;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() => _erreur = null);
    try {
      final position = _position ?? await positionActuelle();
      final itineraire = await api.itineraire(position, widget.lat, widget.lng, _mode);
      if (mounted) {
        setState(() {
          _position = position;
          _itineraire = itineraire;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  void _changerMode(ModeTrajet mode) {
    setState(() => _mode = mode);
    stockage.choisirModeTrajet(mode);
    _charger();
  }

  @override
  Widget build(BuildContext context) {
    final it = _itineraire;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Itinéraire'))),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(widget.nom, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            SelecteurMode(mode: _mode, onChanged: _changerMode),
          ]),
        ),
        if (it == null && _erreur == null) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: _erreur != null && it == null
              ? EtatIllustre(illustration: 'hors_ligne', titre: tr('Connexion impossible'), texte: _erreur, action: _charger)
              : it == null
                  ? const SizedBox.shrink()
                  : ClipRRect(
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                      child: Stack(children: [
                        _Carte(key: ValueKey(it), itineraire: it, position: _position!),
                        Positioned(left: 12, right: 12, bottom: 12, child: _Resume(itineraire: it, position: _position!)),
                      ]),
                    ),
        ),
      ]),
    );
  }
}

class _Carte extends StatelessWidget {
  const _Carte({super.key, required this.itineraire, required this.position});

  final Itineraire itineraire;
  final Position position;

  @override
  Widget build(BuildContext context) {
    final points = [for (final (lat, lng) in itineraire.points) LatLng(lat, lng)];
    final arrivee = points.last;
    return FlutterMap(
      options: MapOptions(
        initialCameraFit: CameraFit.bounds(
          bounds: LatLngBounds.fromPoints(points),
          padding: const EdgeInsets.fromLTRB(48, 48, 48, 150),
          maxZoom: 17,
        ),
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'cd.dawa.dawa',
        ),
        PolylineLayer(polylines: [
          Polyline(
            points: points,
            strokeWidth: 6,
            color: Couleurs.emeraude,
            borderStrokeWidth: 2,
            borderColor: Colors.white,
            pattern: itineraire.parLaRoute ? const StrokePattern.solid() : StrokePattern.dashed(segments: const [12, 8]),
          ),
        ]),
        MarkerLayer(markers: [
          Marker(point: points.first, width: 26, height: 26, child: const _PointDepart()),
          Marker(
            point: arrivee,
            width: 40,
            height: 40,
            alignment: Alignment.topCenter,
            child: const Icon(Icons.location_on, color: Couleurs.rouge, size: 40),
          ),
        ]),
        RichAttributionWidget(attributions: [TextSourceAttribution(tr('© contributeurs OpenStreetMap'))]),
      ],
    );
  }
}

class _PointDepart extends StatelessWidget {
  const _PointDepart();

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Colors.blue,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: ombreDouce,
        ),
      );
}

class _Resume extends StatelessWidget {
  const _Resume({required this.itineraire, required this.position});

  final Itineraire itineraire;
  final Position position;

  @override
  Widget build(BuildContext context) {
    final it = itineraire;
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            Icon(it.mode.icone, color: Couleurs.emeraudeFonce),
            const SizedBox(width: 8),
            Text('${formatDuree(it.minutes)} ${it.mode.maniere}',
                style: theme.textTheme.titleMedium?.copyWith(color: Couleurs.emeraudeFonce, fontWeight: FontWeight.w800)),
            const Spacer(),
            Text(formatDistance(it.distanceKm), style: theme.textTheme.titleSmall),
          ]),
          if (!it.parLaRoute || position.approximative) ...[
            const SizedBox(height: 4),
            Text(
              [
                if (!it.parLaRoute) tr('Trajet exact indisponible : ligne droite et durée estimée.'),
                if (position.approximative) tr('Position indisponible : départ du centre-ville.'),
              ].join(' '),
              style: theme.textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () => itineraireExterne(context, it.points.last.$1, it.points.last.$2),
              icon: const Icon(Icons.open_in_new, size: 16),
              label: Text(tr('Ouvrir dans Google Maps')),
            ),
          ),
        ]),
      ),
    );
  }
}
