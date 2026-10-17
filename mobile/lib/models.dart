double? _double(dynamic v) => (v as num?)?.toDouble();

DateTime? _date(dynamic v) => v == null ? null : DateTime.parse(v).toLocal();

class Medicament {
  final int id;
  final String dci;
  final String nomCommercial;
  final String dosage;
  final String formeLibelle;
  final bool ordonnanceRequise;

  /// URL de l'image (vraie photo ou illustration générée), absolue ou relative au serveur.
  final String? image;
  final bool imageEstIllustration;

  /// Crédit de la photo (auteur et licence, ex. Wikimedia Commons) ; vide si aucun.
  final String imageCredit;

  /// JSON d'origine, conservé pour le stockage local (historique).
  final Map<String, dynamic> json;

  Medicament.fromJson(this.json)
      : id = json['id'],
        dci = json['dci'],
        nomCommercial = json['nom_commercial'],
        dosage = json['dosage'] ?? '',
        formeLibelle = json['forme_libelle'] ?? '',
        ordonnanceRequise = json['ordonnance_requise'] ?? false,
        image = json['image'],
        imageEstIllustration = json['image_est_illustration'] ?? false,
        imageCredit = json['image_credit'] ?? '';

  String get libelle => [nomCommercial, dosage].where((s) => s.isNotEmpty).join(' ');
}

class Pharmacie {
  final int id;
  final String nom;
  final String adresse;
  final String quartier;
  final String telephone;
  final String whatsapp;
  final String horaires;
  final double lat;
  final double lng;
  final double? distanceKm;
  final bool deGarde;

  /// JSON d'origine, conservé pour le stockage local (favoris, cache hors ligne).
  final Map<String, dynamic> json;

  Pharmacie.fromJson(this.json)
      : id = json['id'],
        nom = json['nom'],
        adresse = json['adresse'] ?? '',
        quartier = json['quartier'] ?? '',
        telephone = json['telephone'] ?? '',
        whatsapp = json['whatsapp'] ?? '',
        horaires = json['horaires'] ?? '',
        lat = _double(json['lat'])!,
        lng = _double(json['lng'])!,
        distanceKm = _double(json['distance_km']),
        deGarde = json['de_garde'] ?? false;
}

/// Façon de se rendre à la pharmacie (codes de l'API : pied, moto, voiture).
enum ModeTrajet {
  pied('pied'),
  moto('moto'),
  voiture('voiture');

  const ModeTrajet(this.code);
  final String code;

  static ModeTrajet depuis(String? code) => values.firstWhere((m) => m.code == code, orElse: () => moto);
}

class Trajet {
  final double distanceKm;
  final int minutes;

  /// Vrai si la distance vient du routage par la route, faux si c'est une estimation.
  final bool parLaRoute;

  Trajet.fromJson(Map<String, dynamic> json)
      : distanceKm = _double(json['distance_km'])!,
        minutes = json['minutes'],
        parLaRoute = json['source'] == 'route';
}

/// Tracé d'un trajet par la route (ou ligne droite si le routage est indisponible).
class Itineraire {
  final ModeTrajet mode;
  final List<(double, double)> points;
  final double distanceKm;
  final int minutes;
  final bool parLaRoute;

  Itineraire.fromJson(Map<String, dynamic> json)
      : mode = ModeTrajet.depuis(json['mode']),
        points = [for (final p in json['points'] as List) (_double(p[0])!, _double(p[1])!)],
        distanceKm = _double(json['distance_km'])!,
        minutes = json['minutes'],
        parLaRoute = json['source'] == 'route';
}

/// Trajets et délai pour obtenir le médicament dans une pharmacie (calculés par le serveur).
class Acces {
  /// null : horaires inconnus.
  final bool? ouverte;
  final int? ouvreDansMin;
  final Map<ModeTrajet, Trajet> trajets;

  /// Trajet + attente de l'ouverture ; null si la pharmacie reste fermée toute la semaine.
  final Map<ModeTrajet, int?> delaiMin;

  Acces.fromJson(Map<String, dynamic> json)
      : ouverte = json['ouverte'],
        ouvreDansMin = json['ouvre_dans_min'],
        trajets = {
          for (final e in (json['trajets'] as Map).entries)
            ModeTrajet.depuis(e.key): Trajet.fromJson(e.value),
        },
        delaiMin = {
          for (final e in (json['delai_min'] as Map).entries) ModeTrajet.depuis(e.key): e.value as int?,
        };
}

class Resultat {
  final Pharmacie pharmacie;
  final Medicament medicament;
  final int? prix;
  final bool confirme;
  final double? distanceKm;
  final Acces? acces;

  Resultat.fromJson(Map<String, dynamic> json)
      : pharmacie = Pharmacie.fromJson(json['pharmacie']),
        medicament = Medicament.fromJson(json['medicament']),
        prix = json['prix'],
        confirme = json['confirme'] ?? false,
        distanceKm = _double(json['distance_km']),
        acces = json['acces'] == null ? null : Acces.fromJson(json['acces']);
}

class ReponseRecherche {
  final Medicament? medicament;
  final List<Resultat> resultats;

  ReponseRecherche.fromJson(Map<String, dynamic> json)
      : medicament = json['medicament'] == null ? null : Medicament.fromJson(json['medicament']),
        resultats = (json['resultats'] as List).map((r) => Resultat.fromJson(r)).toList();
}

/// Un produit disponible dans la fiche d'une pharmacie.
class ProduitEnStock {
  final Medicament medicament;
  final int? prix;
  final bool confirme;

  ProduitEnStock.fromJson(Map<String, dynamic> json)
      : medicament = Medicament.fromJson(json['medicament']),
        prix = json['prix'],
        confirme = json['confirme'] ?? false;
}

enum StatutReservation {
  enAttente('en_attente'),
  acceptee('acceptee'),
  prete('prete'),
  retiree('retiree'),
  refusee('refusee'),
  annulee('annulee'),
  expiree('expiree');

  const StatutReservation(this.code);
  final String code;

  static StatutReservation depuis(String code) =>
      values.firstWhere((s) => s.code == code, orElse: () => expiree);

  bool get estActive => this == enAttente || this == acceptee || this == prete;
}

class Reservation {
  final int id;
  final Pharmacie pharmacie;
  final Medicament medicament;
  final int quantite;
  final StatutReservation statut;
  final String statutLibelle;
  final String messagePharmacie;
  final int? prixUnitaire;
  final DateTime creeLe;
  final DateTime expireLe;

  Reservation.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        pharmacie = Pharmacie.fromJson(json['pharmacie']),
        medicament = Medicament.fromJson(json['medicament']),
        quantite = json['quantite'],
        statut = StatutReservation.depuis(json['statut']),
        statutLibelle = json['statut_libelle'] ?? '',
        messagePharmacie = json['message_pharmacie'] ?? '',
        prixUnitaire = json['prix_unitaire'],
        creeLe = _date(json['cree_le'])!,
        expireLe = _date(json['expire_le'])!;

  int? get total => prixUnitaire == null ? null : prixUnitaire! * quantite;
}

class Alerte {
  final int id;
  final Medicament medicament;
  final int rayonKm;
  final DateTime creeLe;
  final DateTime? declencheeLe;
  final Pharmacie? pharmacie;

  Alerte.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        medicament = Medicament.fromJson(json['medicament']),
        rayonKm = json['rayon_km'],
        creeLe = _date(json['cree_le'])!,
        declencheeLe = _date(json['declenchee_le']),
        pharmacie = json['pharmacie'] == null ? null : Pharmacie.fromJson(json['pharmacie']);

  bool get declenchee => declencheeLe != null;
}

class Etablissement {
  final int id;
  final String nom;
  final String type;
  final String typeLibelle;
  final String adresse;
  final String quartier;
  final String telephone;
  final bool urgences24h;
  final String services;
  final double lat;
  final double lng;
  final double? distanceKm;

  Etablissement.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        nom = json['nom'],
        type = json['type'],
        typeLibelle = json['type_libelle'] ?? '',
        adresse = json['adresse'] ?? '',
        quartier = json['quartier'] ?? '',
        telephone = json['telephone'] ?? '',
        urgences24h = json['urgences_24h'] ?? false,
        services = json['services'] ?? '',
        lat = _double(json['lat'])!,
        lng = _double(json['lng'])!,
        distanceKm = _double(json['distance_km']);
}

class ResultatVerification {
  /// conforme, expire, rappele, contrefait ou inconnu.
  final String resultat;
  final String message;
  final String? numeroLot;
  final String fabricant;
  final DateTime? dateExpiration;
  final String note;
  final Medicament? medicament;

  ResultatVerification.fromJson(Map<String, dynamic> json)
      : resultat = json['resultat'],
        message = json['message'],
        numeroLot = json['lot']?['numero'],
        fabricant = json['lot']?['fabricant'] ?? '',
        dateExpiration = json['lot']?['date_expiration'] == null ? null : DateTime.parse(json['lot']['date_expiration']),
        note = json['lot']?['note'] ?? '',
        medicament = json['lot']?['medicament'] == null ? null : Medicament.fromJson(json['lot']['medicament']);
}

class Question {
  final int id;
  final String texte;
  final Medicament? medicament;
  final String statut;
  final String statutLibelle;
  final String reponse;
  final String? reponduPar;
  final DateTime creeLe;
  final DateTime? reponduLe;

  Question.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        texte = json['texte'],
        medicament = json['medicament'] == null ? null : Medicament.fromJson(json['medicament']),
        statut = json['statut'],
        statutLibelle = json['statut_libelle'] ?? '',
        reponse = json['reponse'] ?? '',
        reponduPar = json['repondu_par'],
        creeLe = _date(json['cree_le'])!,
        reponduLe = _date(json['repondu_le']);

  bool get estRepondue => statut != 'en_attente';
}
