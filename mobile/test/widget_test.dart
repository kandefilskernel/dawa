import 'package:dawa/models.dart';
import 'package:dawa/widgets/pharmacie_carte.dart';
import 'package:dawa/widgets/trajet.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('formatPrix groupe les milliers', () {
    expect(formatPrix(500), '500 FC');
    expect(formatPrix(4500), '4 500 FC');
    expect(formatPrix(125000), '125 000 FC');
  });

  test('formatDistance', () {
    expect(formatDistance(0.15), '150 m');
    expect(formatDistance(2.54), '2,5 km');
  });

  test('formatDuree', () {
    expect(formatDuree(8), '8 min');
    expect(formatDuree(60), '1 h');
    expect(formatDuree(65), '1 h 05');
    expect(formatDuree(34 * 60), '1 j');
  });

  test('phrase du délai selon le mode et les horaires', () {
    Acces acces(bool? ouverte, int? delaiMoto) => Acces.fromJson({
          'ouverte': ouverte,
          'ouvre_dans_min': ouverte == false ? 120 : null,
          'trajets': {'moto': {'distance_km': 2.3, 'minutes': 8, 'source': 'route'}},
          'delai_min': {'moto': delaiMoto},
        });
    expect(phraseAcces(acces(true, 8), ModeTrajet.moto), 'Disponible en 8 min à moto');
    expect(phraseAcces(acces(false, 128), ModeTrajet.moto), "Fermée : disponible dans 2 h 08 (à l'ouverture)");
    expect(phraseAcces(acces(false, null), ModeTrajet.moto), 'Fermée cette semaine');
    expect(acces(true, 8).trajets[ModeTrajet.moto]!.parLaRoute, isTrue);
  });
}
