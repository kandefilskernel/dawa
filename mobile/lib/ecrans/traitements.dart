import 'package:flutter/material.dart';

import '../langue.dart';
import '../rappels.dart';
import '../theme.dart';
import '../widgets/communs.dart';

/// Rappels de traitement : prises du jour à cocher, liste des traitements.
class VueTraitements extends StatelessWidget {
  const VueTraitements({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder(
      valueListenable: rappels.traitements,
      builder: (context, traitements, _) {
        final aujourdhui = DateTime.now();
        final actifs = traitements.where((t) => t.estActifLe(aujourdhui)).toList();
        final prises = [
          for (final t in actifs)
            for (final h in t.heures) (traitement: t, minutes: h),
        ]..sort((a, b) => a.minutes.compareTo(b.minutes));

        return ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
          if (!rappels.notificationsDisponibles)
            Container(
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Couleurs.ambreClair, borderRadius: BorderRadius.circular(14)),
              child: Text(
                tr('Sur ce support, les rappels s\'affichent ici mais ne sonnent pas. Installez l\'app Android pour recevoir une notification à chaque prise.'),
                style: TextStyle(color: Color(0xFF92400E), fontSize: 12.5),
              ),
            ),
          FilledButton.icon(
            onPressed: () => _ouvrirFormulaire(context),
            icon: const Icon(Icons.add_alarm),
            label: Text(tr('Ajouter un traitement')),
          ),
          const SizedBox(height: 20),
          if (traitements.isEmpty)
            EtatIllustre(
              illustration: 'reservation_vide',
              titre: tr('Aucun traitement suivi'),
              texte: tr('Ajoutez votre traitement : Dawa vous rappelle chaque prise et le renouvellement.'),
            )
          else ...[
            Text(tr('Aujourd\'hui'), style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            if (prises.isEmpty)
              Text(tr('Aucune prise prévue aujourd\'hui.'), style: Theme.of(context).textTheme.bodySmall)
            else
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(children: [
                  for (var i = 0; i < prises.length; i++) ...[
                    if (i > 0) const Divider(indent: 16, endIndent: 16),
                    _LignePrise(traitement: prises[i].traitement, minutes: prises[i].minutes, jour: aujourdhui),
                  ],
                ]),
              ),
            const SizedBox(height: 24),
            Text(tr('Mes traitements'), style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            for (final t in traitements) ...[_CarteTraitement(traitement: t), const SizedBox(height: 10)],
          ],
        ]);
      },
    );
  }
}

class _LignePrise extends StatelessWidget {
  const _LignePrise({required this.traitement, required this.minutes, required this.jour});

  final Traitement traitement;
  final int minutes;
  final DateTime jour;

  @override
  Widget build(BuildContext context) {
    final pris = traitement.estPris(jour, minutes);
    final maintenant = DateTime.now();
    final enRetard = !pris && maintenant.hour * 60 + maintenant.minute > minutes + 30;
    return CheckboxListTile(
      value: pris,
      onChanged: (_) => rappels.basculerPrise(traitement, jour, minutes),
      activeColor: Couleurs.emeraude,
      secondary: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: pris ? Couleurs.menthe : (enRetard ? const Color(0xFFFEE2E2) : Couleurs.fond),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(formatHeure(minutes),
            style: TextStyle(
              fontWeight: FontWeight.w800,
              color: pris ? Couleurs.emeraudeFonce : (enRetard ? Couleurs.rouge : Couleurs.texte),
            )),
      ),
      title: Text(traitement.nom,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            decoration: pris ? TextDecoration.lineThrough : null,
          )),
      subtitle: Text(pris ? tr('Pris ✓') : (enRetard ? tr('En retard — {dose}', {'dose': traitement.dose}) : traitement.dose)),
    );
  }
}

class _CarteTraitement extends StatelessWidget {
  const _CarteTraitement({required this.traitement});

  final Traitement traitement;

  @override
  Widget build(BuildContext context) {
    final t = traitement;
    final fin = t.fin;
    final joursRestants = fin?.difference(DateTime.now()).inDays;
    String deux(int n) => n.toString().padLeft(2, '0');
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
        child: Row(children: [
          const IconeTeintee(Icons.alarm, taille: 44),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(t.nom, style: const TextStyle(fontWeight: FontWeight.w700)),
              Text([
                if (t.dose.isNotEmpty) t.dose,
                t.heures.map(formatHeure).join(', '),
              ].join(' · '), style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              if (t.estTermine)
                Pastille(tr('Terminé'), couleur: Couleurs.texteDoux)
              else if (fin == null)
                Pastille(tr('Au long cours'), couleur: Couleurs.indigo)
              else
                Pastille(
                  joursRestants! <= 2
                      ? tr('Se termine le {date} — pensez au renouvellement', {'date': '${deux(fin.day)}/${deux(fin.month)}'})
                      : tr('Jusqu\'au {date}', {'date': '${deux(fin.day)}/${deux(fin.month)}'}),
                  couleur: joursRestants <= 2 ? const Color(0xFFB45309) : Couleurs.emeraude,
                ),
              if (t.note.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(t.note, style: Theme.of(context).textTheme.bodySmall),
              ],
            ]),
          ),
          IconButton(
            tooltip: tr('Supprimer'),
            icon: const Icon(Icons.delete_outline, color: Couleurs.texteDoux),
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: Text(tr('Supprimer ce traitement ?')),
                  content: Text(tr('Les rappels de « {nom} » seront arrêtés.', {'nom': t.nom})),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('Annuler'))),
                    FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('Supprimer'))),
                  ],
                ),
              );
              if (ok == true) await rappels.supprimer(t);
            },
          ),
        ]),
      ),
    );
  }
}

Future<void> _ouvrirFormulaire(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    builder: (_) => const _FormulaireTraitement(),
  );
}

class _FormulaireTraitement extends StatefulWidget {
  const _FormulaireTraitement();

  @override
  State<_FormulaireTraitement> createState() => _FormulaireTraitementState();
}

class _FormulaireTraitementState extends State<_FormulaireTraitement> {
  final _nom = TextEditingController();
  final _dose = TextEditingController(text: tr('1 comprimé'));
  final _note = TextEditingController();
  final List<int> _heures = [8 * 60, 20 * 60];
  int? _duree = 7;

  static const _durees = <int?>[3, 5, 7, 10, 14, 30, null];

  @override
  void dispose() {
    _nom.dispose();
    _dose.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _ajouterHeure() async {
    final heure = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 12, minute: 0));
    if (heure == null) return;
    final minutes = heure.hour * 60 + heure.minute;
    if (!_heures.contains(minutes)) setState(() => _heures..add(minutes)..sort());
  }

  Future<void> _enregistrer() async {
    if (_nom.text.trim().isEmpty || _heures.isEmpty) return;
    await rappels.ajouter(
      nom: _nom.text.trim(),
      dose: _dose.text.trim(),
      heures: _heures,
      debut: DateTime.now(),
      dureeJours: _duree,
      note: _note.text.trim(),
    );
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(tr('Nouveau traitement'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(tr('Recopiez l\'ordonnance ou les conseils de votre pharmacien.'),
                style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 16),
            TextField(
              controller: _nom,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(labelText: tr('Médicament (ex. Amoxicilline 500 mg)'), fillColor: Couleurs.fond),
            ),
            const SizedBox(height: 10),
            TextField(controller: _dose, decoration: InputDecoration(labelText: tr('Dose par prise'), fillColor: Couleurs.fond)),
            const SizedBox(height: 16),
            Text(tr('Heures de prise'), style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final h in _heures)
                InputChip(
                  label: Text(formatHeure(h)),
                  onDeleted: () => setState(() => _heures.remove(h)),
                ),
              ActionChip(avatar: const Icon(Icons.add, size: 18), label: Text(tr('Heure')), onPressed: _ajouterHeure),
            ]),
            const SizedBox(height: 16),
            Text(tr('Durée'), style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final d in _durees)
                ChoiceChip(
                  label: Text(d == null ? tr('Au long cours') : tr('{n} jours', {'n': d})),
                  selected: _duree == d,
                  showCheckmark: false,
                  onSelected: (_) => setState(() => _duree = d),
                ),
            ]),
            const SizedBox(height: 16),
            TextField(controller: _note, decoration: InputDecoration(labelText: tr('Note (ex. après le repas)'), fillColor: Couleurs.fond)),
            const SizedBox(height: 20),
            FilledButton(onPressed: _enregistrer, child: Text(tr('Enregistrer et activer les rappels'))),
            const SizedBox(height: 8),
            Text(tr('Dawa ne remplace pas l\'avis de votre médecin ou pharmacien.'),
                textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      ),
    );
  }
}
