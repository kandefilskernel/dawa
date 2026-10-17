import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/image_medicament.dart';

/// Vérification d'un numéro de lot, et signalement d'un produit suspect.
class EcranVerification extends StatefulWidget {
  const EcranVerification({super.key});

  @override
  State<EcranVerification> createState() => _EcranVerificationState();
}

class _EcranVerificationState extends State<EcranVerification> {
  final _lot = TextEditingController();
  ResultatVerification? _resultat;
  String? _erreur;
  bool _chargement = false;

  @override
  void dispose() {
    _lot.dispose();
    super.dispose();
  }

  Future<void> _verifier() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _chargement = true;
      _erreur = null;
    });
    try {
      final resultat = await api.verifierLot(_lot.text.trim());
      if (mounted) setState(() => _resultat = resultat);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    } finally {
      if (mounted) setState(() => _chargement = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(tr('Vérifier un médicament'))),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 32), children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(gradient: Couleurs.degradeMarque, borderRadius: BorderRadius.circular(24)),
          child: Row(children: [
            Icon(Icons.verified_user_outlined, color: Colors.white, size: 40),
            SizedBox(width: 14),
            Expanded(
              child: Text(
                tr('Saisissez le numéro de lot imprimé sur la boîte (souvent « Lot » ou « LOT/BN ») pour savoir s\'il a été rappelé ou signalé comme contrefait.'),
                style: TextStyle(color: Colors.white, height: 1.35),
              ),
            ),
          ]),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _lot,
          textCapitalization: TextCapitalization.characters,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _verifier(),
          decoration: InputDecoration(
            labelText: tr('Numéro de lot'),
            hintText: tr('ex. DEMO-C001'),
            prefixIcon: Icon(Icons.qr_code_2),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _chargement ? null : _verifier,
          icon: _chargement
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.search),
          label: Text(tr('Vérifier')),
        ),
        if (_erreur != null) ...[
          const SizedBox(height: 12),
          Text(_erreur!, style: const TextStyle(color: Couleurs.rouge, fontWeight: FontWeight.w600)),
        ],
        if (_resultat != null) ...[const SizedBox(height: 20), _CarteResultat(resultat: _resultat!)],
        const SizedBox(height: 28),
        Text(tr('Un produit vous semble suspect ?'), style: theme.textTheme.titleMedium),
        const SizedBox(height: 6),
        Text(tr('Emballage mal imprimé, comprimés d\'aspect inhabituel, prix anormalement bas, lot inconnu… Signalez-le : l\'équipe Uzima transmet aux autorités.'), style: theme.textTheme.bodySmall),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => ouvrirSignalement(context, numeroLot: _lot.text.trim(), medicament: _resultat?.medicament),
          icon: const Icon(Icons.report_outlined),
          label: Text(tr('Signaler un produit suspect')),
        ),
      ]),
    );
  }
}

class _CarteResultat extends StatelessWidget {
  const _CarteResultat({required this.resultat});

  final ResultatVerification resultat;

  @override
  Widget build(BuildContext context) {
    final (couleur, fond, icone, titre) = switch (resultat.resultat) {
      'conforme' => (Couleurs.emeraude, const Color(0xFFECFDF5), Icons.verified, tr('Lot conforme')),
      'expire' => (const Color(0xFFB45309), Couleurs.ambreClair, Icons.event_busy, tr('Produit périmé')),
      'rappele' => (Couleurs.rouge, const Color(0xFFFEF2F2), Icons.warning_amber_rounded, tr('Lot rappelé')),
      'contrefait' => (Couleurs.rouge, const Color(0xFFFEF2F2), Icons.gpp_bad_outlined, tr('Contrefaçon signalée')),
      _ => (Couleurs.texteDoux, Colors.white, Icons.help_outline, tr('Lot inconnu')),
    };
    final m = resultat.medicament;
    final exp = resultat.dateExpiration;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: fond,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: couleur.withValues(alpha: 0.4), width: 1.5),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(icone, color: couleur, size: 32),
          const SizedBox(width: 10),
          Text(titre, style: TextStyle(color: couleur, fontSize: 20, fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 10),
        Text(tr(resultat.message), style: const TextStyle(height: 1.4)),
        if (m != null) ...[
          const SizedBox(height: 14),
          Row(children: [
            ImageMedicament(m, taille: 52),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(m.libelle, style: const TextStyle(fontWeight: FontWeight.w700)),
                Text([
                  if (resultat.numeroLot != null) tr('Lot {numero}', {'numero': resultat.numeroLot}),
                  if (resultat.fabricant.isNotEmpty) resultat.fabricant,
                  if (exp != null) tr('exp. {date}', {'date': '${exp.month.toString().padLeft(2, '0')}/${exp.year}'}),
                ].join(' · '), style: Theme.of(context).textTheme.bodySmall),
              ]),
            ),
          ]),
        ],
        if (resultat.note.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(resultat.note, style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 13)),
        ],
      ]),
    );
  }
}

/// Formulaire de signalement (photo facultative).
Future<void> ouvrirSignalement(BuildContext context, {String numeroLot = '', Medicament? medicament}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    builder: (_) => _FormulaireSignalement(numeroLot: numeroLot, medicament: medicament),
  );
}

class _FormulaireSignalement extends StatefulWidget {
  const _FormulaireSignalement({required this.numeroLot, this.medicament});

  final String numeroLot;
  final Medicament? medicament;

  @override
  State<_FormulaireSignalement> createState() => _FormulaireSignalementState();
}

class _FormulaireSignalementState extends State<_FormulaireSignalement> {
  late final _lot = TextEditingController(text: widget.numeroLot);
  final _lieu = TextEditingController();
  final _description = TextEditingController();
  final _telephone = TextEditingController();
  XFile? _photo;
  bool _envoi = false;
  String? _erreur;

  @override
  void dispose() {
    for (final c in [_lot, _lieu, _description, _telephone]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _choisirPhoto(ImageSource source) async {
    final photo = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (photo != null) setState(() => _photo = photo);
  }

  Future<void> _envoyer() async {
    setState(() {
      _envoi = true;
      _erreur = null;
    });
    try {
      await api.signaler(
        description: _description.text.trim(),
        numeroLot: _lot.text.trim(),
        lieuAchat: _lieu.text.trim(),
        telephone: _telephone.text.trim(),
        medicament: widget.medicament,
        photo: _photo == null ? null : await _photo!.readAsBytes(),
        nomPhoto: _photo?.name,
      );
      if (!mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('Merci, votre signalement a été transmis à l\'équipe Uzima.')),
      ));
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    } finally {
      if (mounted) setState(() => _envoi = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(tr('Signaler un produit suspect'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            TextField(controller: _lot, decoration: InputDecoration(labelText: tr('Numéro de lot (si visible)'), fillColor: Couleurs.fond)),
            const SizedBox(height: 10),
            TextField(controller: _lieu, decoration: InputDecoration(labelText: tr('Où l\'avez-vous acheté ?'), fillColor: Couleurs.fond)),
            const SizedBox(height: 10),
            TextField(
              controller: _description,
              maxLines: 3,
              maxLength: 1000,
              decoration: InputDecoration(labelText: tr('Qu\'est-ce qui vous inquiète ?'), fillColor: Couleurs.fond),
            ),
            TextField(
              controller: _telephone,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(labelText: tr('Téléphone pour vous recontacter (facultatif)'), fillColor: Couleurs.fond),
            ),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _choisirPhoto(ImageSource.camera),
                  icon: const Icon(Icons.photo_camera_outlined, size: 18),
                  label: Text(tr('Photo')),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _choisirPhoto(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_outlined, size: 18),
                  label: Text(tr('Galerie')),
                ),
              ),
            ]),
            if (_photo != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Row(children: [
                  const Icon(Icons.check_circle, color: Couleurs.emeraude, size: 18),
                  const SizedBox(width: 6),
                  Expanded(child: Text(tr('Photo jointe : {nom}', {'nom': _photo!.name}), overflow: TextOverflow.ellipsis)),
                ]),
              ),
            if (_erreur != null) ...[
              const SizedBox(height: 10),
              Text(_erreur!, style: const TextStyle(color: Couleurs.rouge, fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _envoi ? null : _envoyer,
              child: _envoi
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(tr('Envoyer le signalement')),
            ),
          ]),
        ),
      ),
    );
  }
}
