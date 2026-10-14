import 'package:flutter/foundation.dart';

/// Adresse de l'API. Surcharger avec `--dart-define=API_URL=https://api.exemple.cd`.
/// Par défaut : localhost en web, 10.0.2.2 depuis l'émulateur Android (= le PC hôte).
String get apiUrl {
  const defini = String.fromEnvironment('API_URL');
  if (defini.isNotEmpty) return defini;
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8010';
  }
  return 'http://localhost:8010';
}

/// Centre-ville de Lubumbashi, utilisé si la position du téléphone est indisponible.
const centreLat = -11.664;
const centreLng = 27.479;

const rayonsKm = [2, 5, 10, 20];
const rayonParDefautKm = 5;
