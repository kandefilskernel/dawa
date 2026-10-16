import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../notifications_push.dart';
import '../theme.dart';
import 'espace.dart';
import 'garde.dart';
import 'recherche.dart';
import 'sante.dart';

class Accueil extends StatefulWidget {
  const Accueil({super.key});

  @override
  State<Accueil> createState() => _AccueilState();
}

class _AccueilState extends State<Accueil> {
  static const _ongletEspace = 3;

  final _espace = GlobalKey<EcranEspaceState>();
  int _onglet = 0;
  int _alertesDeclenchees = 0;

  @override
  void initState() {
    super.initState();
    _verifierAlertes();
    notificationsPush.ouvertures.addListener(_ouvrirEspace);
    notificationsPush.recues.addListener(_notificationRecue);
    // Autorisation demandée une fois l'accueil affiché (Android 13+ l'exige dans un écran visible).
    WidgetsBinding.instance.addPostFrameCallback((_) => notificationsPush.activer());
    if (notificationsPush.ouvertures.value > 0) {
      // App lancée en touchant une notification.
      WidgetsBinding.instance.addPostFrameCallback((_) => _ouvrirEspace());
    }
  }

  @override
  void dispose() {
    notificationsPush.ouvertures.removeListener(_ouvrirEspace);
    notificationsPush.recues.removeListener(_notificationRecue);
    super.dispose();
  }

  /// Une notification touchée (réservation, alerte, réponse) mène à « Mon espace ».
  void _ouvrirEspace() {
    if (mounted) _allerA(_ongletEspace);
  }

  void _notificationRecue() {
    _verifierAlertes();
    if (_onglet == _ongletEspace) _espace.currentState?.rafraichir();
  }

  /// Badge des alertes déclenchées ; aussi rafraîchi à chaque notification reçue app ouverte.
  Future<void> _verifierAlertes() async {
    try {
      final alertes = await api.alertes();
      if (mounted) setState(() => _alertesDeclenchees = alertes.where((a) => a.declenchee).length);
    } on ApiException {
      // Hors ligne : le badge sera mis à jour plus tard.
    }
  }

  void _allerA(int onglet) {
    setState(() => _onglet = onglet);
    if (onglet == _ongletEspace) _espace.currentState?.rafraichir();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _onglet, children: [
        EcranRecherche(
          onVoirGarde: () => _allerA(1),
          onVoirTraitements: () {
            _allerA(_ongletEspace);
            _espace.currentState?.afficherTraitements();
          },
        ),
        const EcranGarde(),
        const EcranSante(),
        EcranEspace(
          key: _espace,
          onAlertesVues: (n) => setState(() => _alertesDeclenchees = n),
        ),
      ]),
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(border: Border(top: BorderSide(color: Couleurs.bordure))),
        child: NavigationBar(
          selectedIndex: _onglet,
          onDestinationSelected: _allerA,
          destinations: [
            NavigationDestination(
              icon: Icon(Icons.search),
              selectedIcon: Icon(Icons.search, color: Couleurs.emeraudeFonce),
              label: tr('Rechercher'),
            ),
            NavigationDestination(
              icon: Icon(Icons.nightlight_outlined),
              selectedIcon: Icon(Icons.nightlight_round, color: Couleurs.emeraudeFonce),
              label: tr('De garde'),
            ),
            NavigationDestination(
              icon: Icon(Icons.local_hospital_outlined),
              selectedIcon: Icon(Icons.local_hospital, color: Couleurs.emeraudeFonce),
              label: tr('Santé'),
            ),
            NavigationDestination(
              icon: Badge(
                isLabelVisible: _alertesDeclenchees > 0,
                label: Text('$_alertesDeclenchees'),
                child: const Icon(Icons.person_outline),
              ),
              selectedIcon: const Icon(Icons.person, color: Couleurs.emeraudeFonce),
              label: tr('Mon espace'),
            ),
          ],
        ),
      ),
    );
  }
}
