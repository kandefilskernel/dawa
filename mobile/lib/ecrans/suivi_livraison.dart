import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../api.dart';
import '../langue.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import '../widgets/trajet.dart';

Future<void> ouvrirSuiviLivraison(BuildContext context, Reservation reservation) => Navigator.of(context)
    .push(MaterialPageRoute(builder: (_) => EcranSuiviLivraison(reservation: reservation)));

/// Le livreur avance sur la carte ; l'heure d'arrivée suit sa vitesse réelle.
class EcranSuiviLivraison extends StatefulWidget {
  const EcranSuiviLivraison({super.key, required this.reservation});

  final Reservation reservation;

  @override
  State<EcranSuiviLivraison> createState() => _EcranSuiviLivraisonState();
}

class _EcranSuiviLivraisonState extends State<EcranSuiviLivraison> {
  static const _intervalle = Duration(seconds: 10);
  SuiviLivraison? _suivi;
  String? _erreur;
  Timer? _minuteur;

  @override
  void initState() {
    super.initState();
    _charger();
    _minuteur = Timer.periodic(_intervalle, (_) => _charger());
  }

  @override
  void dispose() {
    _minuteur?.cancel();
    super.dispose();
  }

  Future<void> _charger() async {
    try {
      final suivi = await api.suiviLivraison(widget.reservation.id);
      if (!mounted) return;
      setState(() {
        _suivi = suivi;
        _erreur = null;
      });
      if (suivi.statut != StatutReservation.enLivraison) _minuteur?.cancel();
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _suivi;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Suivi de la livraison'))),
      body: s == null
          ? (_erreur != null
              ? EtatIllustre(illustration: 'hors_ligne', titre: tr('Connexion impossible'), texte: _erreur, action: _charger)
              : const Center(child: CircularProgressIndicator()))
          : Stack(children: [
              _carteLivraison(s),
              Positioned(left: 12, right: 12, bottom: 12, child: _Resume(suivi: s, reservation: widget.reservation)),
            ]),
    );
  }

  Widget _carteLivraison(SuiviLivraison s) {
    LatLng point((double, double) p) => LatLng(p.$1, p.$2);
    final points = [point(s.pharmacie), if (s.destination != null) point(s.destination!), if (s.position != null) point(s.position!)];
    return FlutterMap(
      options: MapOptions(
        initialCameraFit: points.length > 1
            ? CameraFit.bounds(
                bounds: LatLngBounds.fromPoints(points),
                padding: const EdgeInsets.fromLTRB(48, 48, 48, 190),
                maxZoom: 16,
              )
            : null,
        initialCenter: points.first,
        initialZoom: 14,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'cd.dawa.dawa',
        ),
        if (s.trace.length > 1)
          PolylineLayer(polylines: [
            Polyline(points: [for (final p in s.trace) point(p)], strokeWidth: 5, color: Couleurs.indigo.withValues(alpha: 0.6)),
          ]),
        MarkerLayer(markers: [
          Marker(
            point: point(s.pharmacie),
            width: 36,
            height: 36,
            child: _Rond(icone: Icons.local_pharmacy, couleur: Couleurs.emeraude),
          ),
          if (s.destination != null)
            Marker(
              point: point(s.destination!),
              width: 40,
              height: 40,
              alignment: Alignment.topCenter,
              child: const Icon(Icons.home_rounded, color: Couleurs.rouge, size: 40),
            ),
          if (s.position != null)
            Marker(
              point: point(s.position!),
              width: 46,
              height: 46,
              child: _Rond(icone: Icons.two_wheeler, couleur: s.positionAncienne ? Couleurs.texteDoux : Couleurs.indigo),
            ),
        ]),
        RichAttributionWidget(attributions: [TextSourceAttribution(tr('© contributeurs OpenStreetMap'))]),
      ],
    );
  }
}

class _Rond extends StatelessWidget {
  const _Rond({required this.icone, required this.couleur});

  final IconData icone;
  final Color couleur;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: couleur,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: ombreDouce,
        ),
        child: Icon(icone, color: Colors.white, size: 20),
      );
}

class _Resume extends StatelessWidget {
  const _Resume({required this.suivi, required this.reservation});

  final SuiviLivraison suivi;
  final Reservation reservation;

  String _heure(DateTime d) => '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final s = suivi;
    final theme = Theme.of(context);
    final String titre;
    final String? details;
    if (s.statut == StatutReservation.livree) {
      titre = tr('Commande livrée');
      details = null;
    } else if (s.statut != StatutReservation.enLivraison) {
      titre = tr(reservation.statutLibelle);
      details = null;
    } else if (s.position == null) {
      titre = tr('Le livreur est en route');
      details = tr('Sa position apparaîtra dès que son téléphone l\'enverra.');
    } else {
      titre = tr('Arrivée vers {heure} · dans {duree}',
          {'heure': _heure(s.arriveeEstimee!), 'duree': formatDuree(s.minutesRestantes!)});
      details = [
        tr('Encore {distance}', {'distance': formatDistance(s.distanceRestanteKm!)}),
        s.vitesseMesuree
            ? tr('vitesse mesurée {v} km/h', {'v': s.vitesseKmh!.round()})
            : tr('vitesse habituelle {v} km/h', {'v': s.vitesseKmh!.round()}),
        if (s.positionAncienne) tr('position reçue à {heure}', {'heure': _heure(s.positionRecueLe!)}),
      ].join(' · ');
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            const Icon(Icons.two_wheeler, color: Couleurs.indigo),
            const SizedBox(width: 8),
            Expanded(
              child: Text(titre,
                  style: theme.textTheme.titleMedium?.copyWith(color: Couleurs.indigo, fontWeight: FontWeight.w800)),
            ),
          ]),
          if (details != null) ...[
            const SizedBox(height: 4),
            Text(details, style: theme.textTheme.bodySmall),
          ],
          if (s.livreurNom != null && s.statut == StatutReservation.enLivraison) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: Text(tr('Livreur : {nom}', {'nom': s.livreurNom}), style: theme.textTheme.bodyMedium)),
              if (s.livreurTelephone != null)
                FilledButton.icon(
                  onPressed: () => appeler(context, s.livreurTelephone!),
                  icon: const Icon(Icons.call, size: 18),
                  label: Text(tr('Appeler')),
                ),
            ]),
          ],
        ]),
      ),
    );
  }
}
