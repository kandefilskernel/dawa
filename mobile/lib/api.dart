import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'langue.dart';
import 'config.dart';
import 'models.dart';
import 'position.dart';
import 'stockage.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}

class Api {
  Api({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  static const _delai = Duration(seconds: 15);
  /// Le jeton vit 180 jours côté serveur ; on le renouvelle bien avant.
  static const _renouvelerApres = Duration(days: 30);
  Future<void>? _jetonEnCours;

  Map<String, String> get _entetes => {
        'Content-Type': 'application/json',
        if (stockage.jeton != null) 'Authorization': 'Bearer ${stockage.jeton}',
      };

  /// Obtient (premier lancement) ou renouvelle le jeton d'appareil signé par le serveur.
  Future<void> _assurerJeton() {
    final date = stockage.jetonDate;
    final aJour = stockage.jeton != null && date != null && DateTime.now().difference(date) < _renouvelerApres;
    if (aJour) return Future.value();
    return _jetonEnCours ??= _demanderJeton().whenComplete(() => _jetonEnCours = null);
  }

  Future<void> _demanderJeton() async {
    final uri = Uri.parse('$apiUrl/api/appareil/jeton/');
    final ancien = stockage.jeton == null ? stockage.ancienClientId : null;
    try {
      var reponse = await _client
          .post(uri, headers: {..._entetes, 'X-Client-Id': ?ancien})
          .timeout(_delai);
      if (reponse.statusCode == 401 || reponse.statusCode == 403) {
        // Jeton expiré ou refusé : on repart avec un nouvel appareil.
        await stockage.oublierJeton();
        reponse = await _client.post(uri, headers: _entetes).timeout(_delai);
      }
      if (reponse.statusCode >= 300) {
        throw ApiException(tr('Erreur du serveur ({code}).', {'code': reponse.statusCode}));
      }
      await stockage.sauverJeton(jsonDecode(utf8.decode(reponse.bodyBytes))['jeton'] as String);
    } on TimeoutException {
      throw ApiException(tr('Le réseau est lent. Réessayez.'));
    } on http.ClientException {
      throw ApiException(tr('Pas de connexion internet, ou serveur injoignable.'));
    }
  }

  Future<dynamic> _requete(String methode, String chemin,
      {Map<String, String>? params, Object? corps, bool nouvelEssai = true}) async {
    await _assurerJeton();
    final uri = Uri.parse('$apiUrl$chemin').replace(queryParameters: params);
    final http.Response reponse;
    try {
      final envoi = switch (methode) {
        'POST' => _client.post(uri, headers: _entetes, body: jsonEncode(corps ?? {})),
        'DELETE' => _client.delete(uri, headers: _entetes),
        _ => _client.get(uri, headers: _entetes),
      };
      reponse = await envoi.timeout(_delai);
    } on TimeoutException {
      throw ApiException(tr('Le réseau est lent. Réessayez.'));
    } on http.ClientException {
      throw ApiException(tr('Pas de connexion internet, ou serveur injoignable.'));
    }
    if (reponse.statusCode == 401 && nouvelEssai) {
      await stockage.oublierJeton();
      return _requete(methode, chemin, params: params, corps: corps, nouvelEssai: false);
    }
    final texte = utf8.decode(reponse.bodyBytes);
    if (reponse.statusCode == 400) throw ApiException(_premierMessage(texte));
    if (reponse.statusCode >= 300) {
      throw ApiException(tr('Erreur du serveur ({code}).', {'code': reponse.statusCode}));
    }
    return texte.isEmpty ? null : jsonDecode(texte);
  }

  /// Extrait un message lisible d'une erreur de validation Django REST Framework.
  String _premierMessage(String texte) {
    try {
      dynamic valeur = jsonDecode(texte);
      while (valeur is Map || valeur is List) {
        valeur = valeur is Map ? valeur.values.first : (valeur as List).first;
      }
      return tr(valeur.toString()); // messages du serveur (en français) traduits s'ils sont connus
    } catch (_) {
      return tr('Requête refusée.');
    }
  }

  Map<String, String> _position(Position position) => {
        'lat': position.lat.toStringAsFixed(5),
        'lng': position.lng.toStringAsFixed(5),
      };

  /// Le téléphone accepte les notifications : jeton Firebase et langue des messages.
  Future<void> enregistrerNotifications(String jeton, String langue) =>
      _requete('POST', '/api/appareil/notifications/', corps: {'jeton': jeton, 'langue': langue});

  Future<List<Medicament>> suggestions(String terme) async {
    final json = await _requete('GET', '/api/medicaments/', params: {'q': terme, 'limit': '8'});
    return (json['results'] as List).map((m) => Medicament.fromJson(m)).toList();
  }

  /// Pharmacies qui ont le médicament, de la plus rapide à la plus lente pour ce mode de trajet.
  Future<ReponseRecherche> rechercher(Medicament medicament, Position position, int rayonKm,
      {ModeTrajet mode = ModeTrajet.moto}) async {
    final json = await _requete('GET', '/api/recherche/', params: {
      'medicament': '${medicament.id}',
      'rayon': '$rayonKm',
      'mode': mode.code,
      ..._position(position),
    });
    return ReponseRecherche.fromJson(json);
  }

  Future<List<Pharmacie>> pharmaciesDeGarde(Position position) async {
    final json = await _requete('GET', '/api/pharmacies/garde/', params: _position(position));
    return (json as List).map((p) => Pharmacie.fromJson(p)).toList();
  }

  Future<List<ProduitEnStock>> produitsPharmacie(int pharmacieId) async {
    final json = await _requete('GET', '/api/pharmacies/$pharmacieId/stock/');
    return (json as List).map((p) => ProduitEnStock.fromJson(p)).toList();
  }

  Future<Reservation> reserver({
    required Pharmacie pharmacie,
    required Medicament medicament,
    required int quantite,
    required String nom,
    required String telephone,
  }) async {
    final json = await _requete('POST', '/api/reservations/', corps: {
      'pharmacie_id': pharmacie.id,
      'medicament_id': medicament.id,
      'quantite': quantite,
      'nom': nom,
      'telephone': telephone,
    });
    return Reservation.fromJson(json);
  }

  Future<List<Reservation>> reservations() async {
    final json = await _requete('GET', '/api/reservations/');
    return (json as List).map((r) => Reservation.fromJson(r)).toList();
  }

  Future<Reservation> annulerReservation(int id) async =>
      Reservation.fromJson(await _requete('POST', '/api/reservations/$id/annuler/'));

  Future<void> creerAlerte(Medicament medicament, Position position, int rayonKm) =>
      _requete('POST', '/api/alertes/', corps: {
        'medicament_id': medicament.id,
        'lat': position.lat,
        'lng': position.lng,
        'rayon_km': rayonKm,
      });

  Future<List<Alerte>> alertes() async {
    final json = await _requete('GET', '/api/alertes/');
    return (json as List).map((a) => Alerte.fromJson(a)).toList();
  }

  Future<void> supprimerAlerte(int id) => _requete('DELETE', '/api/alertes/$id/');

  Future<List<Etablissement>> etablissements(Position position, {String? type, bool urgences = false}) async {
    final json = await _requete('GET', '/api/etablissements/', params: {
      ..._position(position),
      'type': ?type,
      if (urgences) 'urgences': '1',
    });
    return (json as List).map((e) => Etablissement.fromJson(e)).toList();
  }

  /// Médicament correspondant au code-barres scanné, ou null s'il n'est pas au catalogue.
  Future<Medicament?> medicamentParCodeBarres(String code) async {
    final json = await _requete('GET', '/api/medicaments/', params: {'code_barres': code});
    final resultats = json['results'] as List;
    return resultats.isEmpty ? null : Medicament.fromJson(resultats.first);
  }

  Future<ResultatVerification> verifierLot(String numero) async =>
      ResultatVerification.fromJson(await _requete('GET', '/api/verification/', params: {'lot': numero}));

  Future<List<Question>> questions() async {
    final json = await _requete('GET', '/api/questions/');
    return (json as List).map((q) => Question.fromJson(q)).toList();
  }

  Future<Question> poserQuestion(String texte, {Medicament? medicament}) async =>
      Question.fromJson(await _requete('POST', '/api/questions/', corps: {
        'texte': texte,
        if (medicament != null) 'medicament_id': medicament.id,
      }));

  /// Signalement d'un produit suspect, avec photo facultative (envoi multipart).
  Future<void> signaler({
    required String description,
    String numeroLot = '',
    String lieuAchat = '',
    String telephone = '',
    Medicament? medicament,
    List<int>? photo,
    String? nomPhoto,
  }) async {
    await _assurerJeton();
    final requete = http.MultipartRequest('POST', Uri.parse('$apiUrl/api/signalements/'))
      ..headers['Authorization'] = 'Bearer ${stockage.jeton}'
      ..fields.addAll({
        'description': description,
        'numero_lot': numeroLot,
        'lieu_achat': lieuAchat,
        'telephone': telephone,
        if (medicament != null) 'medicament_id': '${medicament.id}',
      });
    if (photo != null) {
      requete.files.add(http.MultipartFile.fromBytes('photo', photo, filename: nomPhoto ?? 'photo.jpg'));
    }
    final http.StreamedResponse reponse;
    try {
      reponse = await _client.send(requete).timeout(const Duration(seconds: 60));
    } on TimeoutException {
      throw ApiException(tr("Le réseau est lent : la photo n'a pas pu être envoyée."));
    } on http.ClientException {
      throw ApiException(tr('Pas de connexion internet, ou serveur injoignable.'));
    }
    final texte = await reponse.stream.bytesToString();
    if (reponse.statusCode == 400) throw ApiException(_premierMessage(texte));
    if (reponse.statusCode >= 300) throw ApiException(tr('Erreur du serveur ({code}).', {'code': reponse.statusCode}));
  }
}

final api = Api();
