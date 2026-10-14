import 'package:geolocator/geolocator.dart' as geo;

import 'config.dart';

class Position {
  final double lat;
  final double lng;

  /// Vrai si on n'a pas pu localiser le téléphone et qu'on utilise le centre-ville.
  final bool approximative;

  const Position(this.lat, this.lng, {this.approximative = false});

  static const centreVille = Position(centreLat, centreLng, approximative: true);
}

Future<Position>? _enCours;

/// Position du téléphone, demandée une seule fois par session.
/// Ne lève jamais : retombe sur le centre-ville en cas de refus ou d'échec.
Future<Position> positionActuelle({bool rafraichir = false}) {
  if (rafraichir || _enCours == null) _enCours = _localiser();
  return _enCours!;
}

Future<Position> _localiser() async {
  try {
    if (!await geo.Geolocator.isLocationServiceEnabled()) return Position.centreVille;
    var permission = await geo.Geolocator.checkPermission();
    if (permission == geo.LocationPermission.denied) {
      permission = await geo.Geolocator.requestPermission();
    }
    if (permission == geo.LocationPermission.denied ||
        permission == geo.LocationPermission.deniedForever) {
      return Position.centreVille;
    }
    final p = await geo.Geolocator.getCurrentPosition(
      locationSettings: const geo.LocationSettings(
        accuracy: geo.LocationAccuracy.medium,
        timeLimit: Duration(seconds: 10),
      ),
    );
    return Position(p.latitude, p.longitude);
  } catch (_) {
    return Position.centreVille;
  }
}
