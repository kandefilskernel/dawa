import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

const _maxHistorique = 6;

/// Données gardées sur le téléphone : jeton d'appareil, favoris, historique, cache hors ligne.
class Stockage {
  late final SharedPreferences _prefs;

  /// Pharmacies favorites, observables par les écrans.
  final favoris = ValueNotifier<List<Pharmacie>>([]);

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    favoris.value = _lireListe('favoris').map(Pharmacie.fromJson).toList();
  }

  /// Jeton d'appareil signé RSA par le serveur (null avant le premier appel).
  String? get jeton => _prefs.getString('jeton');
  DateTime? get jetonDate => DateTime.tryParse(_prefs.getString('jeton_date') ?? '');

  /// Identifiant non signé des anciennes versions : échangé une fois contre un jeton.
  String? get ancienClientId => _prefs.getString('client_id');

  Future<void> sauverJeton(String jeton) async {
    await _prefs.setString('jeton', jeton);
    await _prefs.setString('jeton_date', DateTime.now().toIso8601String());
    await _prefs.remove('client_id');
  }

  Future<void> oublierJeton() async {
    await _prefs.remove('jeton');
    await _prefs.remove('jeton_date');
  }

  // Coordonnées du client, pré-remplies dans le formulaire de réservation.
  String get nom => _prefs.getString('nom') ?? '';
  String get telephone => _prefs.getString('telephone') ?? '';

  Future<void> memoriserCoordonnees(String nom, String telephone) async {
    await _prefs.setString('nom', nom);
    await _prefs.setString('telephone', telephone);
  }

  /// Façon de se déplacer choisie dans les résultats (moto par défaut).
  ModeTrajet get modeTrajet => ModeTrajet.depuis(_prefs.getString('mode_trajet'));
  Future<void> choisirModeTrajet(ModeTrajet mode) => _prefs.setString('mode_trajet', mode.code);

  List<Medicament> get historique => _lireListe('historique').map(Medicament.fromJson).toList();

  Future<void> ajouterHistorique(Medicament medicament) async {
    final liste = historique.where((m) => m.id != medicament.id).toList()..insert(0, medicament);
    await _ecrireListe('historique', liste.take(_maxHistorique).map((m) => m.json).toList());
  }

  Future<void> effacerHistorique() => _prefs.remove('historique');

  bool estFavori(int pharmacieId) => favoris.value.any((p) => p.id == pharmacieId);

  Future<void> basculerFavori(Pharmacie pharmacie) async {
    final liste = estFavori(pharmacie.id)
        ? favoris.value.where((p) => p.id != pharmacie.id).toList()
        : [pharmacie, ...favoris.value];
    favoris.value = liste;
    await _ecrireListe('favoris', liste.map((p) => p.json).toList());
  }

  /// Dernière liste des gardes reçue, pour l'afficher sans réseau.
  Future<void> sauverGardes(List<Pharmacie> pharmacies) async {
    await _ecrireListe('gardes', pharmacies.map((p) => p.json).toList());
    await _prefs.setString('gardes_date', DateTime.now().toIso8601String());
  }

  ({List<Pharmacie> pharmacies, DateTime date})? get gardesEnCache {
    final date = _prefs.getString('gardes_date');
    if (date == null) return null;
    return (pharmacies: _lireListe('gardes').map(Pharmacie.fromJson).toList(), date: DateTime.parse(date));
  }

  List<Map<String, dynamic>> _lireListe(String cle) {
    final brut = _prefs.getString(cle);
    if (brut == null) return [];
    try {
      return (jsonDecode(brut) as List).cast<Map<String, dynamic>>();
    } catch (_) {
      return [];
    }
  }

  Future<void> _ecrireListe(String cle, List<Map<String, dynamic>> liste) =>
      _prefs.setString(cle, jsonEncode(liste));
}

final stockage = Stockage();
