import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../langue.dart';
import '../theme.dart';

/// Illustration vectorielle embarquée dans l'app (aucun téléchargement).
class Illustration extends StatelessWidget {
  const Illustration(this.nom, {super.key, this.hauteur});

  final String nom;
  final double? hauteur;

  @override
  Widget build(BuildContext context) =>
      SvgPicture.asset('assets/illustrations/$nom.svg', height: hauteur);
}

class Pastille extends StatelessWidget {
  const Pastille(this.texte, {super.key, required this.couleur, this.icone, this.plein = false});

  final String texte;
  final Color couleur;
  final IconData? icone;
  final bool plein;

  @override
  Widget build(BuildContext context) {
    final avantPlan = plein ? Colors.white : couleur;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: plein ? couleur : couleur.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (icone != null) ...[Icon(icone, size: 14, color: avantPlan), const SizedBox(width: 4)],
        Flexible(child: Text(texte, style: TextStyle(color: avantPlan, fontSize: 12.5, fontWeight: FontWeight.w700))),
      ]),
    );
  }
}

/// Icône dans un carré arrondi teinté.
class IconeTeintee extends StatelessWidget {
  const IconeTeintee(this.icone, {super.key, this.couleur = Couleurs.emeraude, this.taille = 44});

  final IconData icone;
  final Color couleur;
  final double taille;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: taille,
      height: taille,
      decoration: BoxDecoration(
        color: couleur.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(taille * 0.32),
        border: Border.all(color: couleur.withValues(alpha: 0.08)),
      ),
      child: Icon(icone, color: couleur, size: taille * 0.52),
    );
  }
}

/// État vide ou d'erreur avec illustration posée sur un halo de la couleur de la marque.
class EtatIllustre extends StatelessWidget {
  const EtatIllustre({
    super.key,
    required this.illustration,
    required this.titre,
    this.texte,
    this.libelleAction,
    this.action,
  });

  final String illustration;
  final String titre;
  final String? texte;
  final String? libelleAction;
  final VoidCallback? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 40),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 176,
              height: 176,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: [Couleurs.menthe, Color(0x00D1FAE5)], stops: [0.45, 1]),
              ),
              child: Illustration(illustration, hauteur: 128),
            ),
            const SizedBox(height: 12),
            Text(titre, style: theme.textTheme.titleLarge?.copyWith(fontSize: 19), textAlign: TextAlign.center),
            if (texte != null) ...[
              const SizedBox(height: 8),
              Text(texte!,
                  style: theme.textTheme.bodyMedium?.copyWith(color: Couleurs.texteDoux),
                  textAlign: TextAlign.center),
            ],
            if (action != null) ...[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: action,
                icon: Icon(libelleAction == null ? Icons.refresh_rounded : Icons.arrow_forward_rounded, size: 20),
                label: Text(libelleAction ?? tr('Réessayer')),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

/// Chargement centré, aux couleurs de la marque.
class Chargement extends StatelessWidget {
  const Chargement({super.key});

  @override
  Widget build(BuildContext context) => const Center(
        child: SizedBox(width: 36, height: 36, child: CircularProgressIndicator(strokeWidth: 3.5)),
      );
}

/// Titre de section avec, à droite, une action facultative (« Effacer »…).
class TitreSection extends StatelessWidget {
  const TitreSection(this.titre, {super.key, this.action, this.libelleAction});

  final String titre;
  final String? libelleAction;
  final VoidCallback? action;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Mesures.ecart),
      child: Row(children: [
        Container(
          width: 4,
          height: 18,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Couleurs.emeraudeVif, Couleurs.emeraude],
            ),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(titre,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800, fontSize: 17)),
        ),
        if (action != null)
          TextButton(
            onPressed: action,
            style: TextButton.styleFrom(
              minimumSize: const Size(0, 36),
              padding: const EdgeInsets.symmetric(horizontal: 10),
              visualDensity: VisualDensity.compact,
            ),
            child: Text(libelleAction ?? ''),
          ),
      ]),
    );
  }
}

/// En-tête coloré des onglets principaux : dégradé, cercles décoratifs (rappel du logo),
/// titre, sous-titre, illustration. `bas` accueille un compteur, des onglets ou un champ.
class EnTeteEcran extends StatelessWidget {
  const EnTeteEcran({
    super.key,
    required this.titre,
    this.sousTitre,
    this.degrade = Couleurs.degradeMarque,
    this.illustration,
    this.action,
    this.bas,
    this.paddingBas = 22,
  });

  final String titre;
  final String? sousTitre;
  final Gradient degrade;
  final String? illustration;
  final Widget? action;
  final Widget? bas;
  final double paddingBas;

  @override
  Widget build(BuildContext context) {
    final haut = MediaQuery.paddingOf(context).top;
    // Le texte laisse la place à l'illustration posée en haut à droite.
    final reserveIllustration = illustration != null ? 128.0 : 0.0;
    return Container(
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        gradient: degrade,
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      child: Stack(children: [
        const Positioned(right: -70, top: -90, child: _Cercle(taille: 240, opacite: 0.07)),
        const Positioned(left: -50, bottom: -80, child: _Cercle(taille: 170, opacite: 0.05)),
        if (illustration != null)
          Positioned(right: 4, top: haut + 14, child: Illustration(illustration!, hauteur: 96)),
        Padding(
          padding: EdgeInsets.fromLTRB(Mesures.marge, haut + 18, Mesures.marge, paddingBas),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: Padding(
                  padding: EdgeInsets.only(right: reserveIllustration),
                  child: Text(
                    titre,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 27,
                      height: 1.12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.7,
                    ),
                  ),
                ),
              ),
              ?action,
            ]),
            if (sousTitre != null) ...[
              const SizedBox(height: 8),
              Padding(
                padding: EdgeInsets.only(right: reserveIllustration),
                child: Text(sousTitre!,
                    style: const TextStyle(
                        color: Color(0xDEFFFFFF), fontSize: 14, height: 1.4, fontWeight: FontWeight.w500)),
              ),
            ],
            if (bas != null) ...[const SizedBox(height: 14), bas!],
          ]),
        ),
      ]),
    );
  }
}

class _Cercle extends StatelessWidget {
  const _Cercle({required this.taille, required this.opacite});

  final double taille;
  final double opacite;

  @override
  Widget build(BuildContext context) => Container(
        width: taille,
        height: taille,
        decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white.withValues(alpha: opacite)),
      );
}

/// Étiquette ronde sur un en-tête coloré (compteur, ville…).
class PastilleEnTete extends StatelessWidget {
  const PastilleEnTete(this.texte, {super.key, this.icone, this.point});

  final String texte;
  final IconData? icone;

  /// Couleur d'un petit point lumineux devant le texte (ex. vert = ouvert).
  final Color? point;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (point != null) ...[
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: point,
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: point!.withValues(alpha: 0.6), blurRadius: 6)],
            ),
          ),
          const SizedBox(width: 7),
        ],
        if (icone != null) ...[Icon(icone, size: 15, color: Colors.white), const SizedBox(width: 5)],
        Flexible(
          child: Text(texte, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12.5)),
        ),
      ]),
    );
  }
}

/// Icône adaptée à la forme galénique.
IconData iconeForme(String formeLibelle) {
  final f = formeLibelle.toLowerCase();
  if (f.contains('sirop') || f.contains('suspension')) return Icons.local_drink_outlined;
  if (f.contains('inject')) return Icons.vaccines_outlined;
  if (f.contains('pommade')) return Icons.healing_outlined;
  if (f.contains('sachet')) return Icons.inventory_2_outlined;
  return Icons.medication_outlined;
}
