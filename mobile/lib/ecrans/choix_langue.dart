import 'package:flutter/material.dart';

import '../langue.dart';
import '../theme.dart';
import '../widgets/communs.dart';

/// Phrase d'accueil affichée dans chaque langue, pour que chacun reconnaisse la sienne sans savoir lire les autres.
/// Pas encore de phrase en kiluba : elle sera ajoutée avec les traductions relues (traductions/lu.dart).
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
        child: Stack(children: [
          Positioned(right: -90, top: -110, child: _cercle(300, 0.08)),
          Positioned(left: -80, bottom: -120, child: _cercle(260, 0.06)),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: const [BoxShadow(color: Color(0x40022C22), blurRadius: 30, offset: Offset(0, 12))],
                      ),
                      child: const Illustration('logo', hauteur: 84),
                    ),
                    const SizedBox(height: 16),
                    const Text('Uzima',
                        style: TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w800, letterSpacing: -1.2)),
                    const SizedBox(height: 24),
                    for (final (i, l) in Langue.values.where(_bienvenue.containsKey).indexed)
                      Text(_bienvenue[l]!,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: i == 0 ? Colors.white : const Color(0xCCFFFFFF),
                            fontSize: i == 0 ? 19 : 16,
                            fontWeight: i == 0 ? FontWeight.w700 : FontWeight.w500,
                            height: 1.6,
                          )),
                    const SizedBox(height: 32),
                    for (final l in Langue.values) ...[
                      _BoutonLangue(langue: l),
                      const SizedBox(height: 12),
                    ],
                  ]),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _cercle(double taille, double opacite) => Container(
        width: taille,
        height: taille,
        decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white.withValues(alpha: opacite)),
      );
}

class _BoutonLangue extends StatelessWidget {
  const _BoutonLangue({required this.langue});

  final Langue langue;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [BoxShadow(color: Color(0x26022C22), blurRadius: 18, offset: Offset(0, 8))],
      ),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: () => langues.choisir(langue),
          child: Container(
            height: 68,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(children: [
              Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: const BoxDecoration(color: Couleurs.menthe, shape: BoxShape.circle),
                // Code de la langue (FR, SW, EN) : identique dans toutes les langues.
                child: Text(langue.name.toUpperCase(),
                    style: const TextStyle(color: Couleurs.emeraudeFonce, fontWeight: FontWeight.w800, fontSize: 13)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(langue.nom,
                    style: const TextStyle(color: Couleurs.texte, fontSize: 19, fontWeight: FontWeight.w800)),
              ),
              const Icon(Icons.arrow_forward_rounded, color: Couleurs.emeraude),
            ]),
          ),
        ),
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
            contentPadding: const EdgeInsets.symmetric(horizontal: 24),
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
