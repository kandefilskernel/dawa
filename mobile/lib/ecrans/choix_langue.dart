import 'package:flutter/material.dart';

import '../langue.dart';
import '../theme.dart';
import '../widgets/communs.dart';

/// Phrase d'accueil affichée dans chaque langue, pour que chacun reconnaisse la sienne sans savoir lire les autres.
const _bienvenue = {
  Langue.fr: 'Choisissez votre langue',
  Langue.sw: 'Chagua lugha yako',
  Langue.en: 'Choose your language',
};

/// Premier lancement : trois gros boutons, un par langue. Modifiable ensuite dans « Mon espace ».
class EcranChoixLangue extends StatelessWidget {
  const EcranChoixLangue({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: Couleurs.degradeMarque),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Illustration('logo', hauteur: 72),
                const SizedBox(height: 12),
                const Text('Dawa',
                    style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w800)),
                const SizedBox(height: 24),
                for (final l in Langue.values)
                  Text(_bienvenue[l]!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 17, height: 1.5)),
                const SizedBox(height: 28),
                for (final l in Langue.values) ...[
                  _BoutonLangue(langue: l),
                  const SizedBox(height: 12),
                ],
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class _BoutonLangue extends StatelessWidget {
  const _BoutonLangue({required this.langue});

  final Langue langue;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: Colors.white,
          foregroundColor: Couleurs.emeraudeFonce,
          minimumSize: const Size(0, 64),
          textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
        onPressed: () => langues.choisir(langue),
        child: Text(langue.nom),
      ),
    );
  }
}

/// Liste des langues (depuis « Mon espace »).
Future<void> changerLangue(BuildContext context) async {
  final choisie = await showModalBottomSheet<Langue>(
    context: context,
    showDragHandle: true,
    builder: (_) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        for (final l in Langue.values)
          ListTile(
            minTileHeight: 60,
            leading: Icon(
              l == langues.courante.value ? Icons.radio_button_checked : Icons.radio_button_off,
              color: Couleurs.emeraude,
            ),
            title: Text(l.nom, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            onTap: () => Navigator.of(context).pop(l),
          ),
        const SizedBox(height: 8),
      ]),
    ),
  );
  if (choisie != null) await langues.choisir(choisie);
}
