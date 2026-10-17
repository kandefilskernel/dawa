import 'dart:io';

import 'package:dawa/traductions/en.dart';
import 'package:dawa/traductions/sw.dart';
import 'package:flutter_test/flutter_test.dart';

/// Textes traduits via tr(variable), invisibles pour la recherche des tr('...') littéraux :
/// surtout des libellés et messages envoyés en français par le serveur.
const textesServeur = [
  // Filtres de l'annuaire santé (libellés français traduits à l'affichage)
  'Tous', 'Urgences 24h', 'Hôpitaux', 'Cliniques', 'Centres de santé', 'Laboratoires', 'Maternités',
  // Formes
  'Comprimé', 'Gélule', 'Sirop', 'Injectable', 'Pommade / crème', 'Suspension', 'Sachet', 'Autre',
  // Statuts de réservation
  'En attente de la pharmacie', 'Acceptée', 'Prête', 'En cours de livraison', 'Livrée', 'Retirée',
  'Refusée', 'Annulée', 'Expirée',
  // Établissements de santé
  'Hôpital', 'Clinique', 'Centre de santé', 'Laboratoire', 'Maternité',
  // Questions au pharmacien
  'En attente de réponse', 'Répondue', 'Orientée vers un médecin',
  // Vérification des lots
  'Ce lot est enregistré comme conforme.',
  "Ce lot est connu, mais sa date d'expiration est dépassée : ne l'utilisez pas.",
  "Ce lot a fait l'objet d'un rappel : ne l'utilisez pas et rapportez-le à votre pharmacie.",
  "Ce lot est signalé comme contrefait : ne l'utilisez pas et signalez-nous où vous l'avez acheté.",
  "Ce numéro de lot n'est pas dans notre base. Cela ne veut pas dire que le produit est faux : "
      "notre base est encore incomplète. Vérifiez l'emballage et demandez conseil à votre pharmacien.",
  // Erreurs de validation
  'Saisissez le numéro de lot imprimé sur la boîte (au moins 3 caractères).',
  'Médicament inconnu.', 'Pharmacie inconnue.', 'Tapez au moins 2 caractères.',
  'Cette réservation n\'est plus active.', 'Réservation introuvable.',
  'Ce médicament n\'est plus disponible dans cette pharmacie.',
  'Cette pharmacie ne livre pas encore. Choisissez le retrait.',
  "Cette réservation n'est pas une livraison.",
  'Écrivez le médicament dont vous avez besoin.',
  'Décrivez le problème en quelques mots (10 caractères minimum).',
  'Indiquez l\'adresse de livraison (avenue, numéro, repère).',
  'Numéro de téléphone invalide.',
  'Posez votre question en une phrase (10 caractères minimum).',
  'Vous avez déjà réservé ce médicament dans cette pharmacie.',
  'Vous avez déjà 3 réservations en cours.',
];

/// Clés littérales passées à tr('...') dans lib/.
Set<String> clesDuCode() {
  final appel = RegExp(r'''\btr\(\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")''');
  final cles = <String>{};
  for (final f in Directory('lib').listSync(recursive: true).whereType<File>()) {
    if (!f.path.endsWith('.dart') || f.path.contains('traductions')) continue;
    for (final m in appel.allMatches(f.readAsStringSync())) {
      cles.add((m.group(1) ?? m.group(2)!)
          .replaceAllMapped(RegExp(r'\\(.)'), (e) => e.group(1) == 'n' ? '\n' : e.group(1)!));
    }
  }
  return cles;
}

Set<String> variables(String texte) => RegExp(r'\{(\w+)\}').allMatches(texte).map((m) => m.group(1)!).toSet();

void main() {
  final cles = {...clesDuCode(), ...textesServeur};

  test('le code contient bien des textes à traduire', () {
    expect(cles.length, greaterThan(150));
  });

  for (final (nom, table) in [('sw', sw), ('en', en)]) {
    test('tous les textes ont une traduction ($nom)', () {
      final manquants = cles.where((c) => !table.containsKey(c)).toList()..sort();
      expect(manquants, isEmpty, reason: 'Textes sans traduction $nom :\n${manquants.join('\n')}');
    });

    test('les variables {x} sont conservées ($nom)', () {
      final erreurs = [
        for (final e in table.entries)
          if (!setEquals(variables(e.key), variables(e.value))) '${e.key}  →  ${e.value}',
      ];
      expect(erreurs, isEmpty);
    });

    test('aucune traduction vide ou obsolète ($nom)', () {
      expect(table.values.where((v) => v.trim().isEmpty), isEmpty);
      final obsoletes = table.keys.where((k) => !cles.contains(k)).toList();
      expect(obsoletes, isEmpty, reason: 'Clés qui ne servent plus :\n${obsoletes.join('\n')}');
    });
  }
}

bool setEquals<T>(Set<T> a, Set<T> b) => a.length == b.length && a.containsAll(b);
