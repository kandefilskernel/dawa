import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../position.dart';
import '../stockage.dart';
import '../theme.dart';
import 'pharmacie_carte.dart';
import 'image_medicament.dart';

/// Ouvre le formulaire de réservation. Renvoie la réservation créée, ou null si abandon.
Future<Reservation?> ouvrirReservation(
  BuildContext context, {
  required Pharmacie pharmacie,
  required Medicament medicament,
  int? prix,
  bool livraison = false,
}) async {
  final reservation = await showModalBottomSheet<Reservation>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    builder: (_) => _FormulaireReservation(
        pharmacie: pharmacie, medicament: medicament, prix: prix, livraison: livraison && pharmacie.livraison),
  );
  if (reservation != null && context.mounted) {
    await showDialog(context: context, builder: (_) => _Confirmation(reservation: reservation));
  }
  return reservation;
}

class _FormulaireReservation extends StatefulWidget {
  const _FormulaireReservation({required this.pharmacie, required this.medicament, this.prix, this.livraison = false});

  final Pharmacie pharmacie;
  final Medicament medicament;
  final int? prix;

  /// Ouvrir directement en mode livraison (conseil de l'assistant).
  final bool livraison;

  @override
  State<_FormulaireReservation> createState() => _FormulaireReservationState();
}

class _FormulaireReservationState extends State<_FormulaireReservation> {
  final _formulaire = GlobalKey<FormState>();
  late final _nom = TextEditingController(text: stockage.nom);
  late final _telephone = TextEditingController(text: stockage.telephone);
  final _adresse = TextEditingController();
  int _quantite = 1;
  bool _envoi = false;
  String? _erreur;

  // Livraison à moto (si la pharmacie a un livreur) : à l'adresse où se trouve le téléphone.
  bool _livraison = false;
  Position? _positionLivraison;
  DevisLivraison? _devis;
  String? _erreurLivraison;

  @override
  void dispose() {
    _nom.dispose();
    _telephone.dispose();
    _adresse.dispose();
    super.dispose();
  }

  Future<void> _choisirLivraison(bool livraison) async {
    setState(() {
      _livraison = livraison;
      _erreurLivraison = null;
    });
    if (!livraison || _devis != null) return;
    final position = await positionActuelle();
    if (!mounted) return;
    if (position.approximative) {
      setState(() => _erreurLivraison = tr('Activez la localisation : le livreur a besoin de savoir où vous êtes.'));
      return;
    }
    try {
      final devis = await api.devisLivraison(widget.pharmacie, position);
      if (!mounted) return;
      setState(() {
        _positionLivraison = position;
        _devis = devis;
        if (!devis.possible) _erreurLivraison = tr('Vous êtes trop loin de cette pharmacie pour être livré.');
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreurLivraison = e.message);
    }
  }

  @override
  void initState() {
    super.initState();
    if (widget.livraison) WidgetsBinding.instance.addPostFrameCallback((_) => _choisirLivraison(true));
  }

  bool get _livraisonPrete => _devis?.possible == true && _positionLivraison != null;

  Future<void> _envoyer() async {
    if (!_formulaire.currentState!.validate()) return;
    if (_livraison && !_livraisonPrete) return;
    setState(() {
      _envoi = true;
      _erreur = null;
    });
    try {
      final nom = _nom.text.trim();
      final telephone = _telephone.text.trim();
      final reservation = await api.reserver(
        pharmacie: widget.pharmacie,
        medicament: widget.medicament,
        quantite: _quantite,
        nom: nom,
        telephone: telephone,
        adresseLivraison: _livraison ? _adresse.text.trim() : null,
        positionLivraison: _livraison ? _positionLivraison : null,
      );
      await stockage.memoriserCoordonnees(nom, telephone);
      if (mounted) Navigator.of(context).pop(reservation);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    } finally {
      if (mounted) setState(() => _envoi = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final m = widget.medicament;
    final frais = _livraison ? _devis?.frais : null;
    final total = widget.prix == null ? null : widget.prix! * _quantite + (frais ?? 0);

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Form(
            key: _formulaire,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Center(
                child: Container(width: 40, height: 4,
                    decoration: BoxDecoration(color: Couleurs.bordure, borderRadius: BorderRadius.circular(2))),
              ),
              const SizedBox(height: 16),
              Text(tr('Réserver'), style: theme.textTheme.titleLarge),
              const SizedBox(height: 4),
              Text(
                  _livraison
                      ? tr("La pharmacie prépare la commande et un livreur vous l'apporte à moto.")
                      : tr('La pharmacie met le médicament de côté pendant 2 heures.'),
                  style: theme.textTheme.bodySmall),
              if (widget.pharmacie.livraison) ...[
                const SizedBox(height: 12),
                SegmentedButton<bool>(
                  showSelectedIcon: false,
                  segments: [
                    ButtonSegment(value: false, icon: const Icon(Icons.storefront_outlined, size: 18), label: Text(tr('Je passe la prendre'))),
                    ButtonSegment(value: true, icon: const Icon(Icons.two_wheeler, size: 18), label: Text(tr('Livraison'))),
                  ],
                  selected: {_livraison},
                  onSelectionChanged: (s) => _choisirLivraison(s.first),
                ),
              ],
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: Couleurs.fond, borderRadius: BorderRadius.circular(16)),
                child: Row(children: [
                  ImageMedicament(m, taille: 52),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(m.libelle, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                      Text(widget.pharmacie.nom, style: theme.textTheme.bodySmall),
                    ]),
                  ),
                  _Compteur(
                    valeur: _quantite,
                    onChanged: (q) => setState(() => _quantite = q),
                  ),
                ]),
              ),
              if (m.ordonnanceRequise) ...[
                const SizedBox(height: 12),
                _Avertissement(
                  _livraison
                      ? tr('Médicament sur ordonnance : montrez votre ordonnance au livreur.')
                      : tr('Médicament sur ordonnance : présentez votre ordonnance au retrait.'),
                ),
              ],
              const SizedBox(height: 16),
              TextFormField(
                controller: _nom,
                textCapitalization: TextCapitalization.words,
                decoration: _decoration(tr('Votre nom'), Icons.person_outline),
                validator: (v) => (v ?? '').trim().length < 2 ? tr('Indiquez votre nom') : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _telephone,
                keyboardType: TextInputType.phone,
                decoration: _decoration(tr('Téléphone (ex. +243 99 000 0000)'), Icons.phone_outlined),
                validator: (v) => (v ?? '').replaceAll(RegExp(r'[^0-9]'), '').length < 9
                    ? tr('Numéro invalide')
                    : null,
              ),
              if (_livraison) ...[
                const SizedBox(height: 12),
                TextFormField(
                  controller: _adresse,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: _decoration(tr('Adresse (avenue, numéro, repère)'), Icons.home_outlined),
                  validator: (v) => (v ?? '').trim().length < 5 ? tr("Indiquez l'adresse de livraison (avenue, numéro, repère).") : null,
                ),
                const SizedBox(height: 8),
                if (_erreurLivraison != null)
                  Text(_erreurLivraison!, style: const TextStyle(color: Couleurs.rouge, fontWeight: FontWeight.w600))
                else if (_devis == null)
                  const LinearProgressIndicator(minHeight: 2)
                else
                  Text(
                    tr('Livraison : {frais} ({distance})',
                        {'frais': formatPrix(_devis!.frais), 'distance': formatDistance(_devis!.distanceKm)}),
                    style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700),
                  ),
              ],
              if (_erreur != null) ...[
                const SizedBox(height: 12),
                Text(_erreur!, style: const TextStyle(color: Couleurs.rouge, fontWeight: FontWeight.w600)),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _envoi || (_livraison && !_livraisonPrete) ? null : _envoyer,
                child: _envoi
                    ? const SizedBox(width: 20, height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : Text(total == null ? tr('Confirmer la réservation') : tr('Réserver · {prix}', {'prix': formatPrix(total)})),
              ),
              const SizedBox(height: 8),
              Text(_livraison ? tr('Paiement au livreur, à la livraison.') : tr('Paiement à la pharmacie, au moment du retrait.'),
                  textAlign: TextAlign.center, style: theme.textTheme.bodySmall),
            ]),
          ),
        ),
      ),
    );
  }

  InputDecoration _decoration(String libelle, IconData icone) => InputDecoration(
        labelText: libelle,
        prefixIcon: Icon(icone),
        fillColor: Couleurs.fond,
      );
}

class _Compteur extends StatelessWidget {
  const _Compteur({required this.valeur, required this.onChanged});

  final int valeur;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Couleurs.bordure),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        IconButton(
          tooltip: tr('Une boîte de moins'),
          icon: const Icon(Icons.remove, size: 20),
          onPressed: valeur > 1 ? () => onChanged(valeur - 1) : null,
        ),
        Text('$valeur', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
        IconButton(
          tooltip: tr('Une boîte de plus'),
          icon: const Icon(Icons.add, size: 20),
          onPressed: valeur < 10 ? () => onChanged(valeur + 1) : null,
        ),
      ]),
    );
  }
}

class _Avertissement extends StatelessWidget {
  const _Avertissement(this.texte);

  final String texte;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: const Color(0xFFFEE2E2), borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        const Icon(Icons.receipt_long, color: Couleurs.rouge, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Text(texte, style: const TextStyle(color: Color(0xFF991B1B), fontSize: 13))),
      ]),
    );
  }
}

class _Confirmation extends StatelessWidget {
  const _Confirmation({required this.reservation});

  final Reservation reservation;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 72,
            height: 72,
            decoration: const BoxDecoration(gradient: Couleurs.degradeMarque, shape: BoxShape.circle),
            child: const Icon(Icons.check_rounded, color: Colors.white, size: 40),
          ),
          const SizedBox(height: 16),
          Text(tr('Réservation envoyée'), style: theme.textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            tr('{pharmacie} va confirmer votre demande. Suivez-la dans « Mon espace ».',
                {'pharmacie': reservation.pharmacie.nom}),
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(color: Couleurs.texteDoux),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(onPressed: () => Navigator.of(context).pop(), child: Text(tr('Compris'))),
          ),
        ]),
      ),
    );
  }
}
