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
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: plein ? couleur : couleur.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
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
      ),
      child: Icon(icone, color: couleur, size: taille * 0.52),
    );
  }
}

/// État vide ou d'erreur avec illustration.
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
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Illustration(illustration, hauteur: 150),
          const SizedBox(height: 20),
          Text(titre, style: theme.textTheme.titleMedium, textAlign: TextAlign.center),
          if (texte != null) ...[
            const SizedBox(height: 6),
            Text(texte!, style: theme.textTheme.bodyMedium?.copyWith(color: Couleurs.texteDoux),
                textAlign: TextAlign.center),
          ],
          if (action != null) ...[
            const SizedBox(height: 20),
            FilledButton(onPressed: action, child: Text(libelleAction ?? tr('Réessayer'))),
          ],
        ]),
      ),
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
