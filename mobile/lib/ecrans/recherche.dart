import 'dart:async';

import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import 'assistant.dart';
import 'conseil.dart';
import 'resultats.dart';
import 'scanner.dart';
import 'verification.dart';
import '../widgets/image_medicament.dart';
import '../widgets/recherche_vocale.dart';

const _recherchesFrequentes = ['Paracétamol', 'Amoxicilline', 'Coartem', 'SRO', 'Ibuprofène', 'Flagyl'];

class EcranRecherche extends StatefulWidget {
  const EcranRecherche({super.key, required this.onVoirGarde, required this.onVoirTraitements});

  final VoidCallback onVoirGarde;
  final VoidCallback onVoirTraitements;

  @override
  State<EcranRecherche> createState() => _EcranRechercheState();
}

class _EcranRechercheState extends State<EcranRecherche> {
  final _champ = TextEditingController();
  final _focus = FocusNode();
  Timer? _attente;
  List<Medicament> _suggestions = [];
  String? _erreur;
  bool _chargement = false;
  int _requete = 0;

  @override
  void initState() {
    super.initState();
    _focus.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _attente?.cancel();
    _champ.dispose();
    _focus.dispose();
    super.dispose();
  }

  String get _terme => _champ.text.trim();

  void _surSaisie(String texte) {
    _attente?.cancel();
    if (texte.trim().length < 2) {
      setState(() {
        _suggestions = [];
        _erreur = null;
      });
      return;
    }
    // On attend que l'utilisateur arrête de taper : économise les données mobiles.
    _attente = Timer(const Duration(milliseconds: 350), () => _charger(texte.trim()));
    setState(() {});
  }

  /// Le nom dicté remplit le champ et lance la recherche, comme s'il avait été tapé.
  Future<void> _dicter() async {
    final nom = await dicterNomMedicament(context);
    if (nom != null && mounted) _choisirFrequent(nom);
  }

  void _choisirFrequent(String nom) {
    _champ.value = TextEditingValue(text: nom, selection: TextSelection.collapsed(offset: nom.length));
    _focus.requestFocus();
    _attente?.cancel();
    _charger(nom);
  }

  Future<void> _charger(String terme) async {
    final numero = ++_requete;
    setState(() => _chargement = true);
    try {
      final suggestions = await api.suggestions(terme);
      if (numero != _requete || !mounted) return;
      setState(() {
        _suggestions = suggestions;
        _erreur = null;
      });
    } on ApiException catch (e) {
      if (numero != _requete || !mounted) return;
      setState(() => _erreur = e.message);
    } finally {
      if (numero == _requete && mounted) setState(() => _chargement = false);
    }
  }

  void _ouvrir(Medicament medicament) {
    _focus.unfocus();
    stockage.ajouterHistorique(medicament).then((_) {
      if (mounted) setState(() {});
    });
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => EcranResultats(medicament: medicament)),
    );
  }

  void _effacer() {
    _champ.clear();
    _surSaisie('');
  }

  @override
  Widget build(BuildContext context) {
    final saisieActive = _terme.isNotEmpty || _focus.hasFocus;
    return Column(children: [
      _EnTete(compact: saisieActive, champ: _champRecherche()),
      Expanded(child: _terme.length >= 2 ? _resultatsSaisie() : _decouverte()),
    ]);
  }

  Widget _champRecherche() {
    return DecoratedBox(
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), boxShadow: ombreDouce),
      child: TextField(
        controller: _champ,
        focusNode: _focus,
        onChanged: _surSaisie,
        textInputAction: TextInputAction.search,
        onSubmitted: (_) {
          if (_suggestions.isNotEmpty) _ouvrir(_suggestions.first);
        },
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        decoration: InputDecoration(
          hintText: tr('Nom du médicament'),
          prefixIcon: const Padding(
            padding: EdgeInsets.only(left: 6),
            child: Icon(Icons.search, color: Couleurs.emeraude, size: 26),
          ),
          suffixIcon: _chargement
              ? const Padding(
                  padding: EdgeInsets.all(16),
                  child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                )
              : _terme.isEmpty
                  ? Row(mainAxisSize: MainAxisSize.min, children: [
                      IconButton(
                        tooltip: tr('Chercher à la voix'),
                        icon: const Icon(Icons.mic, color: Couleurs.emeraude, size: 28),
                        onPressed: _dicter,
                      ),
                      IconButton(
                        tooltip: tr('Scanner la boîte'),
                        icon: const Icon(Icons.qr_code_scanner, color: Couleurs.emeraude),
                        onPressed: () => scannerBoite(context),
                      ),
                      const SizedBox(width: 4),
                    ])
                  : IconButton(tooltip: tr('Effacer'), icon: const Icon(Icons.close_rounded), onPressed: _effacer),
        ),
      ),
    );
  }

  Widget _decouverte() {
    final theme = Theme.of(context);
    final recents = stockage.historique;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
      children: [
        if (recents.isNotEmpty) ...[
          Row(children: [
            Text(tr('Recherches récentes'), style: theme.textTheme.titleMedium),
            const Spacer(),
            TextButton(
              onPressed: () async {
                await stockage.effacerHistorique();
                setState(() {});
              },
              child: Text(tr('Effacer')),
            ),
          ]),
          const SizedBox(height: 4),
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              for (var i = 0; i < recents.length; i++) ...[
                if (i > 0) const Divider(indent: 56),
                ListTile(
                  leading: ImageMedicament(recents[i], taille: 44),
                  title: Text(recents[i].libelle, style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text(recents[i].dci),
                  trailing: const Icon(Icons.history, size: 20, color: Couleurs.texteDoux),
                  onTap: () => _ouvrir(recents[i]),
                ),
              ],
            ]),
          ),
          const SizedBox(height: 28),
        ],
        Text(tr('Recherches fréquentes'), style: theme.textTheme.titleMedium),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final nom in _recherchesFrequentes)
            ActionChip(
              avatar: const Icon(Icons.medication_outlined, size: 18, color: Couleurs.emeraude),
              label: Text(nom),
              onPressed: () => _choisirFrequent(nom),
            ),
        ]),
        const SizedBox(height: 20),
        Card(
          clipBehavior: Clip.antiAlias,
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            leading: const IconeTeintee(Icons.assistant_outlined),
            title: Text(tr("Besoin d'un médicament vite ?"), style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(tr("Demandez à l'assistant : la pharmacie la plus rapide, réserver ou se faire livrer.")),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EcranAssistant())),
          ),
        ),
        const SizedBox(height: 28),
        Text(tr('Services'), style: theme.textTheme.titleMedium),
        const SizedBox(height: 12),
        // Pas de hauteur fixe : les cartes grandissent avec la taille de texte choisie sur le téléphone.
        _GrilleDeux(
          children: [
            _Service(
              icone: Icons.qr_code_scanner, titre: tr('Scanner une boîte'), texte: tr('Code-barres'),
              couleur: Couleurs.emeraude, onTap: () => scannerBoite(context),
            ),
            _Service(
              icone: Icons.verified_user_outlined, titre: tr('Vérifier un lot'), texte: tr('Anti-contrefaçon'),
              couleur: const Color(0xFF0369A1),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EcranVerification())),
            ),
            _Service(
              icone: Icons.forum_outlined, titre: tr('Pharmacien en ligne'), texte: tr('Posez une question'),
              couleur: Couleurs.indigo,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EcranConseil())),
            ),
            _Service(
              icone: Icons.alarm, titre: tr('Mes rappels'), texte: tr('Prises et renouvellement'),
              couleur: Couleurs.ambreFonce, onTap: widget.onVoirTraitements,
            ),
          ],
        ),
        const SizedBox(height: 28),
        _CarteGarde(onTap: widget.onVoirGarde),
        const SizedBox(height: 28),
        Text(tr('Comment ça marche'), style: theme.textTheme.titleMedium),
        const SizedBox(height: 12),
        IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: _Etape(icone: Icons.search, titre: tr('Cherchez'), texte: tr('Tapez ou dites le nom du médicament'))),
          SizedBox(width: 10),
          Expanded(child: _Etape(icone: Icons.compare_arrows, titre: tr('Comparez'), texte: tr('Prix et distance'), couleur: Couleurs.ambreFonce)),
          SizedBox(width: 10),
          Expanded(child: _Etape(icone: Icons.call, titre: tr('Appelez'), texte: tr('La pharmacie le garde'), couleur: Couleurs.indigo)),
        ])),
        const SizedBox(height: 24),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.info_outline, size: 16, color: Couleurs.texteDoux),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              tr('Uzima vous informe et vous oriente. Pour tout conseil sur un traitement, demandez à votre pharmacien ou à votre médecin.'),
              style: theme.textTheme.bodySmall,
            ),
          ),
        ]),
      ],
    );
  }

  Widget _resultatsSaisie() {
    if (_erreur != null) {
      return EtatIllustre(
        illustration: 'hors_ligne',
        titre: tr('Connexion impossible'),
        texte: _erreur,
        action: () => _charger(_terme),
      );
    }
    if (_suggestions.isEmpty) {
      if (_chargement) return const SizedBox.shrink();
      return EtatIllustre(
        illustration: 'recherche_vide',
        titre: tr('Aucun médicament trouvé'),
        texte: tr('Vérifiez l\'orthographe de « {terme} » ou essayez le nom de la molécule.', {'terme': _terme}),
      );
    }
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(_suggestions.length > 1 ? tr('{n} médicaments', {'n': _suggestions.length}) : tr('{n} médicament', {'n': _suggestions.length}),
              style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700)),
        ),
        Card(
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            for (var i = 0; i < _suggestions.length; i++) ...[
              if (i > 0) const Divider(indent: 72),
              _LigneMedicament(medicament: _suggestions[i], onTap: () => _ouvrir(_suggestions[i])),
            ],
          ]),
        ),
      ],
    );
  }
}

class _EnTete extends StatelessWidget {
  const _EnTete({required this.compact, required this.champ});

  final bool compact;
  final Widget champ;

  @override
  Widget build(BuildContext context) {
    final haut = MediaQuery.paddingOf(context).top;
    return Container(
      decoration: const BoxDecoration(
        gradient: Couleurs.degradeMarque,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      padding: EdgeInsets.fromLTRB(20, haut + 16, 20, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Illustration('logo', hauteur: 36),
          const SizedBox(width: 10),
          const Text('Uzima',
              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.place, size: 16, color: Colors.white),
              SizedBox(width: 4),
              Text('Lubumbashi', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            ]),
          ),
        ]),
        AnimatedSize(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOutCubic,
          child: compact
              ? const SizedBox(height: 16, width: double.infinity)
              : Padding(
                  padding: const EdgeInsets.only(top: 12, bottom: 8),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
                    Expanded(
                      flex: 5,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(tr('Votre médicament,\nà deux pas.'),
                            style: TextStyle(color: Colors.white, fontSize: 26, height: 1.15,
                                fontWeight: FontWeight.w800, letterSpacing: -0.6)),
                        SizedBox(height: 8),
                        Text(tr('Disponibilité, prix et distance\ndes pharmacies autour de vous.'),
                            style: TextStyle(color: Color(0xE6FFFFFF), fontSize: 13.5, height: 1.35)),
                      ]),
                    ),
                    const Expanded(flex: 4, child: Illustration('pharmacie', hauteur: 130)),
                  ]),
                ),
        ),
        champ,
      ]),
    );
  }
}

class _LigneMedicament extends StatelessWidget {
  const _LigneMedicament({required this.medicament, required this.onTap});

  final Medicament medicament;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final m = medicament;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(children: [
          ImageMedicament(m, taille: 52),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.libelle, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text([m.dci, tr(m.formeLibelle)].where((s) => s.isNotEmpty).join(' · '),
                  style: theme.textTheme.bodySmall),
              if (m.ordonnanceRequise) ...[
                const SizedBox(height: 6),
                Pastille(tr('Sur ordonnance'), couleur: Couleurs.rouge, icone: Icons.receipt_long),
              ],
            ]),
          ),
          const Icon(Icons.chevron_right, color: Couleurs.texteDoux),
        ]),
      ),
    );
  }
}

class _CarteGarde extends StatelessWidget {
  const _CarteGarde({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: Ink(
          decoration: BoxDecoration(
            gradient: Couleurs.degradeNuit,
            borderRadius: BorderRadius.circular(24),
            boxShadow: ombreDouce,
          ),
          child: Row(children: [
            Expanded(
              child: Padding(
                padding: EdgeInsets.fromLTRB(20, 20, 0, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('Pharmacies de garde'),
                      style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                  SizedBox(height: 6),
                  Text(tr('Ouvertes la nuit et le dimanche, près de chez vous.'),
                      style: TextStyle(color: Color(0xCCFFFFFF), fontSize: 13, height: 1.3)),
                  SizedBox(height: 14),
                  Row(children: [
                    Text(tr('Voir la liste'),
                        style: TextStyle(color: Color(0xFFFDE68A), fontWeight: FontWeight.w700)),
                    SizedBox(width: 4),
                    Icon(Icons.arrow_forward, size: 16, color: Color(0xFFFDE68A)),
                  ]),
                ]),
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: const Illustration('garde', hauteur: 100),
            ),
          ]),
        ),
      ),
    );
  }
}

class _Etape extends StatelessWidget {
  const _Etape({required this.icone, required this.titre, required this.texte, this.couleur = Couleurs.emeraude});

  final IconData icone;
  final String titre;
  final String texte;
  final Color couleur;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          IconeTeintee(icone, couleur: couleur, taille: 38),
          const SizedBox(height: 10),
          Text(titre, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text(texte, style: theme.textTheme.bodySmall),
        ]),
      ),
    );
  }
}

/// Grille de 2 colonnes dont chaque ligne prend la hauteur de son contenu le plus haut.
class _GrilleDeux extends StatelessWidget {
  const _GrilleDeux({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      for (var i = 0; i < children.length; i += 2) ...[
        if (i > 0) const SizedBox(height: 10),
        IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(child: children[i]),
            const SizedBox(width: 10),
            Expanded(child: i + 1 < children.length ? children[i + 1] : const SizedBox()),
          ]),
        ),
      ],
    ]);
  }
}

class _Service extends StatelessWidget {
  const _Service({required this.icone, required this.titre, required this.texte, required this.couleur, required this.onTap});

  final IconData icone;
  final String titre;
  final String texte;
  final Color couleur;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            IconeTeintee(icone, couleur: couleur, taille: 38),
            const SizedBox(height: 10),
            Text(titre, style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(texte, style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      ),
    );
  }
}
