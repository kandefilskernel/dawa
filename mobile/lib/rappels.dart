import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import 'langue.dart';

/// Nombre de jours programmés d'avance pour un traitement à durée limitée.
/// Le calendrier est reprogrammé à chaque ouverture de l'app.
const _joursProgrammes = 30;

String cleJour(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String formatHeure(int minutes) =>
    '${(minutes ~/ 60).toString().padLeft(2, '0')}h${(minutes % 60).toString().padLeft(2, '0')}';

/// Un traitement suivi par le patient. Tout reste sur le téléphone.
class Traitement {
  Traitement({
    required this.id,
    required this.nom,
    required this.dose,
    required this.heures,
    required this.debut,
    this.dureeJours,
    this.note = '',
    Map<String, List<int>>? prises,
  }) : prises = prises ?? {};

  final int id;
  String nom;
  String dose;

  /// Heures de prise, en minutes depuis minuit (ex. 8h00 → 480).
  List<int> heures;
  DateTime debut;

  /// Null : traitement au long cours (sans fin).
  int? dureeJours;
  String note;

  /// Prises effectuées : jour (aaaa-mm-jj) → minutes cochées.
  final Map<String, List<int>> prises;

  DateTime? get fin => dureeJours == null
      ? null
      : DateTime(debut.year, debut.month, debut.day).add(Duration(days: dureeJours!));

  bool estActifLe(DateTime jour) {
    final j = DateTime(jour.year, jour.month, jour.day);
    final d = DateTime(debut.year, debut.month, debut.day);
    return !j.isBefore(d) && (fin == null || j.isBefore(fin!));
  }

  bool get estTermine => fin != null && !DateTime.now().isBefore(fin!);

  bool estPris(DateTime jour, int minutes) => prises[cleJour(jour)]?.contains(minutes) ?? false;

  void basculerPrise(DateTime jour, int minutes) {
    final liste = prises.putIfAbsent(cleJour(jour), () => []);
    liste.contains(minutes) ? liste.remove(minutes) : liste.add(minutes);
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'nom': nom,
        'dose': dose,
        'heures': heures,
        'debut': debut.toIso8601String(),
        'duree_jours': dureeJours,
        'note': note,
        'prises': prises,
      };

  factory Traitement.fromJson(Map<String, dynamic> json) => Traitement(
        id: json['id'],
        nom: json['nom'],
        dose: json['dose'] ?? '',
        heures: (json['heures'] as List).cast<int>(),
        debut: DateTime.parse(json['debut']),
        dureeJours: json['duree_jours'],
        note: json['note'] ?? '',
        prises: (json['prises'] as Map<String, dynamic>? ?? {})
            .map((k, v) => MapEntry(k, (v as List).cast<int>())),
      );
}

/// Stockage des traitements et programmation des rappels.
class Rappels {
  final _notifications = FlutterLocalNotificationsPlugin();
  late SharedPreferences _prefs;
  bool _notificationsPretes = false;

  final traitements = ValueNotifier<List<Traitement>>([]);

  /// Les notifications programmées ne sont fiables que sur Android pour l'instant.
  bool get notificationsDisponibles => _notificationsPretes;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    traitements.value = _lire();
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      tz_data.initializeTimeZones();
      String zone;
      try {
        zone = (await FlutterTimezone.getLocalTimezone()).identifier;
      } catch (_) {
        zone = 'Africa/Lubumbashi';
      }
      tz.setLocalLocation(tz.getLocation(zone));
      await _notifications.initialize(
        settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
      );
      _notificationsPretes = true;
      await _programmer();
    } catch (e) {
      debugPrint('Rappels indisponibles : $e');
    }
  }

  /// Demande l'autorisation d'afficher des notifications (Android 13+).
  Future<bool> demanderAutorisation() async {
    if (!_notificationsPretes) return false;
    final android = _notifications.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await android?.requestNotificationsPermission() ?? true;
  }

  int _prochainId() {
    final id = (_prefs.getInt('traitement_dernier_id') ?? 0) + 1;
    _prefs.setInt('traitement_dernier_id', id);
    return id;
  }

  Future<void> ajouter({
    required String nom,
    required String dose,
    required List<int> heures,
    required DateTime debut,
    int? dureeJours,
    String note = '',
  }) async {
    final traitement = Traitement(
      id: _prochainId(), nom: nom, dose: dose, heures: [...heures]..sort(),
      debut: debut, dureeJours: dureeJours, note: note,
    );
    traitements.value = [...traitements.value, traitement];
    await _enregistrer();
    await demanderAutorisation();
  }

  Future<void> supprimer(Traitement traitement) async {
    traitements.value = traitements.value.where((t) => t.id != traitement.id).toList();
    await _enregistrer();
  }

  Future<void> basculerPrise(Traitement traitement, DateTime jour, int minutes) async {
    traitement.basculerPrise(jour, minutes);
    traitements.value = [...traitements.value];
    await _sauver();
  }

  List<Traitement> _lire() {
    final brut = _prefs.getString('traitements');
    if (brut == null) return [];
    try {
      return (jsonDecode(brut) as List).map((t) => Traitement.fromJson(t)).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _sauver() =>
      _prefs.setString('traitements', jsonEncode(traitements.value.map((t) => t.toJson()).toList()));

  Future<void> _enregistrer() async {
    await _sauver();
    await _programmer();
  }

  /// Après un changement de langue : textes des notifications à jour.
  void reprogrammer() => _programmer();

  /// Reprogramme toutes les notifications à partir de la liste des traitements.
  Future<void> _programmer() async {
    if (!_notificationsPretes) return;
    await _notifications.cancelAll();
    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        'rappels_traitement',
        tr('Rappels de traitement'),
        channelDescription: tr('Heure de prise de vos médicaments'),
        importance: Importance.high,
        priority: Priority.high,
      ),
    );
    final maintenant = tz.TZDateTime.now(tz.local);
    for (final t in traitements.value.where((t) => !t.estTermine)) {
      for (var i = 0; i < t.heures.length; i++) {
        final minutes = t.heures[i];
        final titre = 'Dawa · ${t.nom}';
        final corps = t.dose.isEmpty
            ? tr('C\'est l\'heure de votre prise.')
            : tr('C\'est l\'heure de votre prise : {dose}.', {'dose': t.dose});
        if (t.fin == null) {
          // Traitement sans fin : une notification quotidienne répétée.
          var prochaine = tz.TZDateTime(tz.local, maintenant.year, maintenant.month, maintenant.day,
              minutes ~/ 60, minutes % 60);
          if (prochaine.isBefore(maintenant)) prochaine = prochaine.add(const Duration(days: 1));
          await _notifications.zonedSchedule(
            id: t.id * 100 + i,
            scheduledDate: prochaine,
            notificationDetails: details,
            androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
            title: titre,
            body: corps,
            matchDateTimeComponents: DateTimeComponents.time,
          );
        } else {
          // Durée limitée : chaque prise jusqu'à la fin (fenêtre glissante de 30 jours).
          for (var jour = 0; jour < _joursProgrammes; jour++) {
            final date = tz.TZDateTime(tz.local, maintenant.year, maintenant.month, maintenant.day + jour,
                minutes ~/ 60, minutes % 60);
            if (date.isBefore(maintenant) || !t.estActifLe(date)) continue;
            await _notifications.zonedSchedule(
              id: t.id * 10000 + jour * 10 + i,
              scheduledDate: date,
              notificationDetails: details,
              androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
              title: titre,
              body: corps,
            );
          }
        }
      }
    }
  }
}

final rappels = Rappels();
