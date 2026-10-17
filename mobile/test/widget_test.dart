import 'package:dawa/ecrans/assistant.dart';
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

  test("réponse de l'assistant composée sans IA", () {
    Map<String, dynamic> resultat({Map<String, dynamic>? livraison}) => {
          'pharmacie': {'id': 1, 'nom': 'Pharmacie Démo Centre', 'lat': -11.66, 'lng': 27.48, 'livraison': true},
          'medicament': {'id': 2, 'dci': 'Amoxicilline', 'nom_commercial': 'Amoxicilline'},
          'prix': 5000,
          'acces': {
            'ouverte': true,
            'trajets': {'pied': {'distance_km': 2.0, 'minutes': 25, 'source': 'route'}},
            'delai_min': {'pied': 25},
          },
          'livraison': ?livraison,
        };
    ReponseAssistant reponse(String action, Map<String, dynamic> rec) => ReponseAssistant.fromJson(
        {'reponse': '', 'source': 'regles', 'situation': 'trouve', 'recommandation': rec, 'action': action, 'mode': 'pied'});

    expect(texteReponse(reponse('reserver', resultat())),
        'Le plus rapide : Pharmacie Démo Centre (5 000 FC). Disponible en 25 min à pied. '
        'Réservez : la pharmacie vous le met de côté.');
    expect(
        texteReponse(reponse('se_faire_livrer', resultat(livraison: {'possible': true, 'minutes': 20, 'frais': 3000}))),
        'Le plus rapide : vous faire livrer par Pharmacie Démo Centre (5 000 FC), chez vous dans environ 20 min, '
        'livraison 3 000 FC.');
    expect(texteReponse(ReponseAssistant.fromJson({'reponse': 'Texte IA', 'source': 'ia'})), 'Texte IA');
  });
}
