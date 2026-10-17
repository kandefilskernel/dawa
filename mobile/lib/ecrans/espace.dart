import 'dart:async';

import 'package:flutter/material.dart';

import '../langue.dart';
import '../notifications_push.dart';
import '../api.dart';
import '../models.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import 'choix_langue.dart';
import 'fiche_pharmacie.dart';
import 'resultats.dart';
import 'suivi_livraison.dart';
import 'traitements.dart';
import '../widgets/image_medicament.dart';

class EcranEspace extends StatefulWidget {
  const EcranEspace({super.key, this.onAlertesVues});

  /// Prévient l'accueil pour mettre à jour le badge de l'onglet.
  final ValueChanged<int>? onAlertesVues;

  @override
  State<EcranEspace> createState() => EcranEspaceState();
}

class EcranEspaceState extends State<EcranEspace> with SingleTickerProviderStateMixin {
  late final _onglets = TabController(length: 4, vsync: this);

  void afficherTraitements() => _onglets.animateTo(2);
  List<Reservation>? _reservations;
  List<Alerte>? _alertes;
  String? _erreur;
  Timer? _horloge;

  @override
  void initState() {
    super.initState();
    rafraichir();
    // Met à jour les comptes à rebours des réservations.
    _horloge = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _horloge?.cancel();
    _onglets.dispose();
    super.dispose();
  }

  Future<void> rafraichir() async {
    setState(() => _erreur = null);
    try {
      final resultats = await Future.wait([api.reservations(), api.alertes()]);
      if (!mounted) return;
      setState(() {
        _reservations = resultats[0] as List<Reservation>;
        _alertes = resultats[1] as List<Alerte>;
      });
      widget.onAlertesVues?.call(_alertes!.where((a) => a.declenchee).length);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  Future<void> _annuler(Reservation r) async {
    final confirme = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(tr('Annuler la réservation ?')),
        content: Text(tr('{medicament} chez {pharmacie}', {'medicament': r.medicament.libelle, 'pharmacie': r.pharmacie.nom})),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('Non'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('Oui, annuler'))),
        ],
      ),
    );
    if (confirme != true) return;
    try {
      await api.annulerReservation(r.id);
      await rafraichir();
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _supprimerAlerte(Alerte a) async {
    try {
      await api.supprimerAlerte(a.id);
      await rafraichir();
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final actives = _reservations?.where((r) => r.statut.estActive).length ?? 0;
    final declenchees = _alertes?.where((a) => a.declenchee).length ?? 0;

    return Column(children: [
      EnTeteEcran(
        titre: tr('Mon espace'),
        sousTitre: tr('Réservations, alertes, rappels de traitement et favoris.'),
        paddingBas: 10,
        // Toujours lisible : le nom de la langue est écrit dans la langue elle-même.
        action: TextButton.icon(
          onPressed: () => changerLangue(context),
          style: TextButton.styleFrom(
            foregroundColor: Colors.white,
            backgroundColor: const Color(0x29FFFFFF),
            shape: const StadiumBorder(side: BorderSide(color: Color(0x38FFFFFF))),
            minimumSize: const Size(0, 38),
            padding: const EdgeInsets.symmetric(horizontal: 12),
          ),
          icon: const Icon(Icons.translate, size: 18),
          label: Text(langues.courante.value.nom),
        ),
        bas: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const _EtatNotifications(),
          const SizedBox(height: 10),
          TabBar(
            controller: _onglets,
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            labelColor: Couleurs.emeraudeFonce,
            unselectedLabelColor: const Color(0xD9FFFFFF),
            indicator: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
            indicatorSize: TabBarIndicatorSize.tab,
            indicatorPadding: const EdgeInsets.symmetric(vertical: 6),
            labelPadding: const EdgeInsets.symmetric(horizontal: 14),
            dividerColor: Colors.transparent,
            overlayColor: const WidgetStatePropertyAll(Color(0x14FFFFFF)),
            splashBorderRadius: BorderRadius.circular(12),
            tabs: [
              Tab(child: _LibelleOnglet(tr('Réservations'), actives)),
              Tab(child: _LibelleOnglet(tr('Alertes'), declenchees)),
              Tab(text: tr('Traitements')),
              Tab(text: tr('Favoris')),
            ],
          ),
        ]),
      ),
      Expanded(
        child: TabBarView(controller: _onglets, children: [
          _liste(_reservations, _carteReservation,
              vide: EtatIllustre(
                illustration: 'reservation_vide',
                titre: tr('Aucune réservation'),
                texte: tr('Réservez un médicament depuis les résultats : la pharmacie le garde 2 heures.'),
              )),
          _liste(_alertes, _carteAlerte,
              vide: EtatIllustre(
                illustration: 'recherche_vide',
                titre: tr('Aucune alerte'),
                texte: tr('Quand un médicament est introuvable, appuyez sur « Me prévenir ».'),
              )),
          const VueTraitements(),
          _favoris(),
        ]),
      ),
    ]);
  }

  Widget _liste<T>(List<T>? elements, Widget Function(T) carte, {required Widget vide}) {
    if (_erreur != null && elements == null) {
      return EtatIllustre(illustration: 'hors_ligne', titre: tr('Connexion impossible'), texte: _erreur, action: rafraichir);
    }
    if (elements == null) return const Chargement();
    return RefreshIndicator(
      onRefresh: rafraichir,
      child: elements.isEmpty
          ? ListView(children: [vide])
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              itemCount: elements.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (_, i) => carte(elements[i]),
            ),
    );
  }

  Widget _favoris() {
    return ValueListenableBuilder(
      valueListenable: stockage.favoris,
      builder: (_, favoris, _) {
        if (favoris.isEmpty) {
          return EtatIllustre(
            illustration: 'favoris_vide',
            titre: tr('Aucune pharmacie favorite'),
            texte: tr('Touchez le cœur sur la fiche d\'une pharmacie pour la retrouver ici.'),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          itemCount: favoris.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (_, i) => PharmacieCarte(pharmacie: favoris[i]),
        );
      },
    );
  }

  Widget _carteReservation(Reservation r) {
    final theme = Theme.of(context);
    final (couleur, icone) = _apparence(r.statut);
    final restant = r.expireLe.difference(DateTime.now());

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Pastille(tr(r.statutLibelle), couleur: couleur, icone: icone, plein: r.statut == StatutReservation.prete),
            const Spacer(),
            if (r.statut.estActive && !restant.isNegative)
              Row(children: [
                const Icon(Icons.timer_outlined, size: 15, color: Couleurs.texteDoux),
                const SizedBox(width: 4),
                Text(tr('Expire dans {duree}', {'duree': _duree(restant)}), style: theme.textTheme.bodySmall),
              ]),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            ImageMedicament(r.medicament, taille: 52),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r.medicament.libelle} × ${r.quantite}',
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                InkWell(
                  onTap: () => ouvrirFichePharmacie(context, r.pharmacie),
                  child: Text(r.pharmacie.nom,
                      style: theme.textTheme.bodySmall?.copyWith(
                          color: Couleurs.emeraude, fontWeight: FontWeight.w600)),
                ),
              ]),
            ),
            if (r.total != null)
              Text(formatPrix(r.total!),
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Couleurs.emeraudeFonce)),
          ]),
          if (r.messagePharmacie.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Couleurs.menthePale,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Couleurs.menthe),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.chat_bubble_outline_rounded, size: 16, color: Couleurs.emeraude),
                const SizedBox(width: 8),
                Expanded(child: Text('« ${r.messagePharmacie} »', style: const TextStyle(fontStyle: FontStyle.italic))),
              ]),
            ),
          ],
          if (r.estLivraison) ...[
            const SizedBox(height: 10),
            Row(children: [
              const Icon(Icons.two_wheeler, size: 16, color: Couleurs.texteDoux),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  [
                    tr('Livraison : {adresse}', {'adresse': r.adresseLivraison}),
                    if (r.fraisLivraison != null) formatPrix(r.fraisLivraison!),
                  ].join(' · '),
                  style: theme.textTheme.bodySmall,
                ),
              ),
            ]),
          ],
          if (r.statut == StatutReservation.enLivraison) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Couleurs.indigo),
                onPressed: () => ouvrirSuiviLivraison(context, r).then((_) => rafraichir()),
                icon: const Icon(Icons.location_searching, size: 18),
                label: Text(tr('Suivre le livreur sur la carte')),
              ),
            ),
          ],
          if (r.statut.estActive && r.statut != StatutReservation.enLivraison) ...[
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: () => appeler(context, r.pharmacie.telephone),
                  icon: const Icon(Icons.call, size: 18),
                  label: Text(tr('Appeler')),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(foregroundColor: Couleurs.rouge),
                  onPressed: () => _annuler(r),
                  child: Text(tr('Annuler')),
                ),
              ),
            ]),
          ],
        ]),
      ),
    );
  }

  Widget _carteAlerte(Alerte a) {
    final theme = Theme.of(context);
    final pharmacie = a.pharmacie;
    return Card(
      color: a.declenchee ? const Color(0xFFECFDF5) : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            // Image du médicament, avec une pastille cloche indiquant l'état de l'alerte.
            Stack(clipBehavior: Clip.none, children: [
              ImageMedicament(a.medicament, taille: 52),
              Positioned(
                right: -6,
                bottom: -6,
                child: Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: a.declenchee ? Couleurs.emeraude : Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 2),
                    boxShadow: ombreDouce,
                  ),
                  child: Icon(a.declenchee ? Icons.notifications_active : Icons.notifications_none,
                      size: 14, color: a.declenchee ? Colors.white : Couleurs.texteDoux),
                ),
              ),
            ]),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(a.medicament.libelle,
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                Text(
                  a.declenchee && pharmacie != null
                      ? tr('Disponible chez {pharmacie} !', {'pharmacie': pharmacie.nom})
                      : tr('On vous prévient dès qu\'il est disponible à moins de {km} km.', {'km': a.rayonKm}),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: a.declenchee ? Couleurs.emeraudeFonce : Couleurs.texteDoux,
                    fontWeight: a.declenchee ? FontWeight.w700 : FontWeight.w400,
                  ),
                ),
              ]),
            ),
            IconButton(
              tooltip: tr('Supprimer l\'alerte'),
              icon: const Icon(Icons.delete_outline, color: Couleurs.texteDoux),
              onPressed: () => _supprimerAlerte(a),
            ),
          ]),
          if (a.declenchee) ...[
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: FilledButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => EcranResultats(medicament: a.medicament))),
                  child: Text(tr('Voir les pharmacies')),
                ),
              ),
              if (pharmacie != null) ...[
                const SizedBox(width: 10),
                OutlinedButton(
                  style: OutlinedButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(48, 46)),
                  onPressed: () => appeler(context, pharmacie.telephone),
                  child: const Icon(Icons.call_outlined, size: 20),
                ),
              ],
            ]),
          ],
        ]),
      ),
    );
  }

  (Color, IconData) _apparence(StatutReservation statut) => switch (statut) {
        StatutReservation.enAttente => (const Color(0xFFB45309), Icons.hourglass_top),
        StatutReservation.acceptee => (Couleurs.emeraude, Icons.thumb_up_alt_outlined),
        StatutReservation.prete => (Couleurs.emeraude, Icons.check_circle),
        StatutReservation.enLivraison => (Couleurs.indigo, Icons.two_wheeler),
        StatutReservation.livree => (Couleurs.texteDoux, Icons.done_all),
        StatutReservation.retiree => (Couleurs.texteDoux, Icons.done_all),
        StatutReservation.refusee => (Couleurs.rouge, Icons.block),
        StatutReservation.annulee => (Couleurs.texteDoux, Icons.close),
        StatutReservation.expiree => (Couleurs.texteDoux, Icons.timer_off_outlined),
      };

  String _duree(Duration d) {
    if (d.inMinutes < 60) return '${d.inMinutes} min';
    return '${d.inHours} h ${(d.inMinutes % 60).toString().padLeft(2, '0')}';
  }
}

class _LibelleOnglet extends StatelessWidget {
  const _LibelleOnglet(this.texte, this.nombre);

  final String texte;
  final int nombre;

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Flexible(child: Text(texte, overflow: TextOverflow.ellipsis)),
      if (nombre > 0) ...[
        const SizedBox(width: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: BoxDecoration(color: Couleurs.ambre, borderRadius: BorderRadius.circular(10)),
          child: Text('$nombre',
              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
        ),
      ],
    ]);
  }
}

/// Notifications sur ce téléphone : actives, ou pourquoi elles ne le sont pas, avec un bouton pour réessayer.
class _EtatNotifications extends StatelessWidget {
  const _EtatNotifications();

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<EtatNotifications>(
      valueListenable: notificationsPush.etat,
      builder: (context, etat, _) {
        if (etat == EtatNotifications.indisponibles) return const SizedBox.shrink();
        final (icone, texte) = switch (etat) {
          EtatNotifications.actives => (Icons.notifications_active, tr('Notifications activées')),
          EtatNotifications.enCours => (Icons.notifications_none, tr('Activation des notifications…')),
          EtatNotifications.refusees => (Icons.notifications_off, tr('Notifications refusées : autorisez-les dans les réglages du téléphone')),
          _ => (Icons.notifications_off, tr('Notifications non activées')),
        };
        const style = TextStyle(color: Color(0xD9FFFFFF), fontSize: 12.5, fontWeight: FontWeight.w500);
        return Row(children: [
          Icon(icone, color: Couleurs.soleil, size: 16),
          const SizedBox(width: 6),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(texte, style: style),
              if (etat == EtatNotifications.erreur && notificationsPush.erreur != null)
                SelectableText(notificationsPush.erreur!, style: style.copyWith(fontSize: 11), maxLines: 3),
            ]),
          ),
          if (etat == EtatNotifications.erreur || etat == EtatNotifications.refusees)
            TextButton(
              onPressed: notificationsPush.activer,
              style: TextButton.styleFrom(foregroundColor: Colors.white, visualDensity: VisualDensity.compact),
              child: Text(tr('Réessayer')),
            ),
        ]);
      },
    );
  }
}
