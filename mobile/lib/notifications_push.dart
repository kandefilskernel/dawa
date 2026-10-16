import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'api.dart';
import 'langue.dart';

/// Projet Firebase, fourni à la compilation :
/// `--dart-define=FIREBASE_API_KEY=… --dart-define=FIREBASE_APP_ID=…`
/// `--dart-define=FIREBASE_SENDER_ID=… --dart-define=FIREBASE_PROJECT_ID=…`
/// Sans ces valeurs, l'app fonctionne sans notifications (alertes vues à l'ouverture).
const _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
const _appId = String.fromEnvironment('FIREBASE_APP_ID');
const _senderId = String.fromEnvironment('FIREBASE_SENDER_ID');
const _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');

/// Canal Android des notifications de suivi (même identifiant que côté serveur).
const _canal = AndroidNotificationChannel(
  'dawa_suivi',
  'Réservations et alertes',
  description: 'Réservation prête, médicament disponible, réponse d\'un pharmacien.',
  importance: Importance.high,
);

/// Notifications envoyées par le serveur : réservation qui avance, médicament redevenu
/// disponible, réponse d'un pharmacien. Android uniquement pour l'instant.
class NotificationsPush {
  final _locales = FlutterLocalNotificationsPlugin();
  String? _jeton;

  /// Incrémenté quand la personne touche une notification : l'accueil ouvre « Mon espace ».
  final ouvertures = ValueNotifier<int>(0);

  /// Incrémenté à chaque notification reçue app ouverte : l'accueil rafraîchit ses badges.
  final recues = ValueNotifier<int>(0);

  bool get _configure => _apiKey.isNotEmpty && _appId.isNotEmpty && _senderId.isNotEmpty && _projectId.isNotEmpty;

  Future<void> init() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android || !_configure) return;
    try {
      await Firebase.initializeApp(
        options: const FirebaseOptions(
          apiKey: _apiKey, appId: _appId, messagingSenderId: _senderId, projectId: _projectId,
        ),
      );
      await _locales
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(_canal);

      final messagerie = FirebaseMessaging.instance;
      // App fermée ou en arrière-plan : Android affiche la notification ; on réagit quand on la touche.
      FirebaseMessaging.onMessageOpenedApp.listen((_) => ouvertures.value++);
      if (await messagerie.getInitialMessage() != null) ouvertures.value++;
      // App ouverte : Android n'affiche rien, on montre la notification nous-mêmes.
      FirebaseMessaging.onMessage.listen(_afficher);

      // Jeton FCM classique (le serveur envoie avec `message.token`) ; register()/onRegistered donne
      // un identifiant d'installation pour un autre mode d'envoi, non utilisé ici.
      // ignore: deprecated_member_use
      messagerie.onTokenRefresh.listen((jeton) => _enregistrer(jeton));
      langues.courante.addListener(() => _enregistrer(_jeton));
      unawaited(_demarrer(messagerie));
    } catch (e) {
      debugPrint('Notifications indisponibles : $e');
    }
  }

  Future<void> _demarrer(FirebaseMessaging messagerie) async {
    try {
      await messagerie.requestPermission();
      // ignore: deprecated_member_use
      await _enregistrer(await messagerie.getToken());
    } catch (e) {
      debugPrint('Jeton de notification indisponible : $e');
    }
  }

  /// Envoie le jeton au serveur, avec la langue des messages. Réessayé au prochain lancement si hors ligne.
  Future<void> _enregistrer(String? jeton) async {
    if (jeton == null) return;
    _jeton = jeton;
    try {
      await api.enregistrerNotifications(jeton, langues.courante.value.name);
    } on ApiException catch (e) {
      debugPrint('Enregistrement des notifications reporté : $e');
    }
  }

  Future<void> _afficher(RemoteMessage message) async {
    recues.value++;
    final notification = message.notification;
    if (notification == null) return;
    await _locales.show(
      id: message.messageId.hashCode & 0x7fffffff,
      title: notification.title,
      body: notification.body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(_canal.id, _canal.name,
            channelDescription: _canal.description, importance: Importance.high, priority: Priority.high),
      ),
    );
  }
}

final notificationsPush = NotificationsPush();
