import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'traductions/en.dart';
import 'traductions/sw.dart';

/// Langues de l'app. Le français est la langue source : les textes du code sont en français
/// et servent de clés aux tables de traduction (traductions/sw.dart, traductions/en.dart).
enum Langue {
  fr('Français'),
  sw('Kiswahili'),
  en('English');

  const Langue(this.nom);

  /// Nom de la langue dans la langue elle-même (affiché tel quel, sans traduction).
  final String nom;

  Locale get locale => Locale(name);
}

class Langues {
  late SharedPreferences _prefs;
  final courante = ValueNotifier<Langue>(Langue.fr);

  /// Vrai tant que la personne n'a jamais choisi sa langue (premier lancement).
  bool get aChoisir => _prefs.getString('langue') == null;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    final enregistree = _prefs.getString('langue');
    courante.value = Langue.values.firstWhere(
      (l) => l.name == (enregistree ?? PlatformDispatcher.instance.locale.languageCode),
      orElse: () => Langue.fr,
    );
  }

  Future<void> choisir(Langue langue) async {
    await _prefs.setString('langue', langue.name);
    courante.value = langue;
  }
}

final langues = Langues();

const _tables = {Langue.sw: sw, Langue.en: en};

/// Traduit un texte français dans la langue choisie.
/// `{nom}` dans le texte est remplacé par `valeurs['nom']`.
/// Un texte absent des tables reste en français (le test traductions_test l'empêche).
String tr(String francais, [Map<String, Object?> valeurs = const {}]) {
  var texte = _tables[langues.courante.value]?[francais] ?? francais;
  valeurs.forEach((cle, valeur) => texte = texte.replaceAll('{$cle}', '${valeur ?? ''}'));
  return texte;
}
