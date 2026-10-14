import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../config.dart';
import '../models.dart';
import '../position.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/carte_pharmacies.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import '../widgets/image_medicament.dart';

class EcranResultats extends StatefulWidget {
  const EcranResultats({super.key, required this.medicament});

  final Medicament medicament;

  @override
  State<EcranResultats> createState() => _EcranResultatsState();
}

class _EcranResultatsState extends State<EcranResultats> {
  int _rayon = rayonParDefautKm;
  bool _surCarte = false;
  Position? _position;
  ReponseRecherche? _reponse;
  String? _erreur;
  bool _chargement = true;
  bool _alerteCreee = false;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() {
      _chargement = true;
      _erreur = null;
    });
    try {
      final position = _position ?? await positionActuelle();
      final reponse = await api.rechercher(widget.medicament, position, _rayon);
      if (!mounted) return;
      setState(() {
        _position = position;
        _reponse = reponse;
      });
      // Met à jour l'historique avec les données fraîches (image comprise).
      final frais = reponse.medicament;
      if (frais != null) stockage.ajouterHistorique(frais);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    } finally {
      if (mounted) setState(() => _chargement = false);
    }
  }

  Future<void> _creerAlerte() async {
    final messager = ScaffoldMessenger.of(context);
    try {
      await api.creerAlerte(widget.medicament, _position ?? await positionActuelle(), 10);
      if (!mounted) return;
      setState(() => _alerteCreee = true);
      messager.showSnackBar(SnackBar(
        content: Text(tr('Alerte créée : vous la retrouverez dans « Mon espace ».')),
      ));
    } on ApiException catch (e) {
      messager.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  void _changerRayon(int rayon) {
    setState(() => _rayon = rayon);
    _charger();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Résultats'))),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
          child: _Resume(medicament: widget.medicament, reponse: _reponse),
        ),
        if (_position?.approximative ?? false)
          Padding(
            padding: EdgeInsets.fromLTRB(20, 10, 20, 0),
            child: Row(children: [
              Icon(Icons.location_off_outlined, size: 16, color: Couleurs.texteDoux),
              SizedBox(width: 6),
              Expanded(
                child: Text(tr('Position indisponible : distances depuis le centre-ville.'),
                    style: TextStyle(fontSize: 13, color: Couleurs.texteDoux)),
              ),
            ]),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Row(children: [
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  for (final r in rayonsKm)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text('$r km'),
                        selected: _rayon == r,
                        showCheckmark: false,
                        onSelected: (_) => _changerRayon(r),
                      ),
                    ),
                ]),
              ),
            ),
            const SizedBox(width: 8),
            SegmentedButton<bool>(
              showSelectedIcon: false,
              style: SegmentedButton.styleFrom(
                selectedBackgroundColor: Couleurs.emeraude,
                selectedForegroundColor: Colors.white,
                backgroundColor: Colors.white,
                side: const BorderSide(color: Couleurs.bordure),
                visualDensity: VisualDensity.compact,
              ),
              segments: [
                ButtonSegment(value: false, icon: Icon(Icons.view_agenda_outlined, size: 18), tooltip: tr('Liste')),
                ButtonSegment(value: true, icon: Icon(Icons.map_outlined, size: 18), tooltip: tr('Carte')),
              ],
              selected: {_surCarte},
              onSelectionChanged: (s) => setState(() => _surCarte = s.first),
            ),
          ]),
        ),
        if (_chargement) const LinearProgressIndicator(minHeight: 2) else const SizedBox(height: 2),
        Expanded(child: _contenu()),
      ]),
    );
  }

  Widget _contenu() {
    if (_chargement && _reponse == null) return const SizedBox.shrink();
    if (_erreur != null && _reponse == null) {
      return EtatIllustre(
        illustration: 'hors_ligne',
        titre: tr('Connexion impossible'),
        texte: _erreur,
        action: _charger,
      );
    }
    final resultats = _reponse!.resultats;
    if (_surCarte) {
      return ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        child: CartePharmacies(
          position: _position!,
          resultats: resultats,
          medicamentRecherche: widget.medicament,
        ),
      );
    }
    if (resultats.isEmpty) {
      final suivant = rayonsKm.where((r) => r > _rayon).firstOrNull;
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(32, 16, 32, 32),
        child: Column(children: [
          const Illustration('recherche_vide', hauteur: 140),
          const SizedBox(height: 16),
          Text(tr('Pas en stock dans un rayon de {km} km', {'km': _rayon}),
              style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
          const SizedBox(height: 6),
          Text(tr("Les pharmacies proches n'ont pas signalé ce médicament."),
              textAlign: TextAlign.center, style: TextStyle(color: Couleurs.texteDoux)),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _alerteCreee ? null : _creerAlerte,
              icon: Icon(_alerteCreee ? Icons.check : Icons.notifications_active_outlined, size: 18),
              label: Text(_alerteCreee ? tr('Alerte activée') : tr('Me prévenir quand il est disponible')),
            ),
          ),
          if (suivant != null) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => _changerRayon(suivant),
                child: Text(tr("Chercher jusqu'à {km} km", {'km': suivant})),
              ),
            ),
          ],
        ]),
      );
    }

    final prixMin = resultats.map((r) => r.prix).whereType<int>().fold<int?>(
        null, (min, p) => min == null || p < min ? p : min);
    final avecPosition = !(_position?.approximative ?? true);

    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        itemCount: resultats.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, i) {
          final r = resultats[i];
          return PharmacieCarte(
            pharmacie: r.pharmacie,
            resultat: r,
            medicamentRecherche: widget.medicament,
            meilleurPrix: prixMin != null && r.prix == prixMin && resultats.length > 1,
            plusProche: i == 0 && avecPosition,
          );
        },
      ),
    );
  }
}

/// En-tête récapitulatif : le médicament et ce qu'on a trouvé.
class _Resume extends StatelessWidget {
  const _Resume({required this.medicament, required this.reponse});

  final Medicament medicament;
  final ReponseRecherche? reponse;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final m = medicament;
    final resultats = reponse?.resultats;
    final nbPharmacies = resultats?.map((r) => r.pharmacie.id).toSet().length;
    final prix = resultats?.map((r) => r.prix).whereType<int>().toList() ?? [];
    prix.sort();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: Couleurs.degradeMarque,
        borderRadius: BorderRadius.circular(24),
        boxShadow: ombreDouce,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          GestureDetector(
            onTap: () => ouvrirImageMedicament(context, m),
            child: Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
              child: ImageMedicament(m, taille: 64, rayon: 15),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.libelle,
                  style: theme.textTheme.titleLarge?.copyWith(color: Colors.white, fontWeight: FontWeight.w800)),
              Text([m.dci, tr(m.formeLibelle)].where((s) => s.isNotEmpty).join(' · '),
                  style: const TextStyle(color: Color(0xD9FFFFFF), fontSize: 13)),
            ]),
          ),
        ]),
        const SizedBox(height: 14),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (nbPharmacies != null)
            _Info(icone: Icons.local_pharmacy_outlined,
                texte: nbPharmacies > 1 ? tr('{n} pharmacies', {'n': nbPharmacies}) : tr('{n} pharmacie', {'n': nbPharmacies})),
          if (prix.isNotEmpty) _Info(icone: Icons.sell_outlined, texte: tr('dès {prix}', {'prix': formatPrix(prix.first)})),
          if (m.ordonnanceRequise)
            _Info(icone: Icons.receipt_long, texte: tr('Sur ordonnance'), alerte: true),
        ]),
      ]),
    );
  }
}

class _Info extends StatelessWidget {
  const _Info({required this.icone, required this.texte, this.alerte = false});

  final IconData icone;
  final String texte;
  final bool alerte;

  @override
  Widget build(BuildContext context) {
    final couleur = alerte ? Couleurs.rouge : Couleurs.emeraudeFonce;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: alerte ? const Color(0xFFFEE2E2) : Colors.white,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icone, size: 15, color: couleur),
        const SizedBox(width: 5),
        Text(texte, style: TextStyle(color: couleur, fontWeight: FontWeight.w700, fontSize: 12.5)),
      ]),
    );
  }
}
