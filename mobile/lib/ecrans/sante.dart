import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../position.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';

// Libellés en français, traduits à l'affichage.
const _filtres = <(String libelle, String? type, bool urgences)>[
  ('Tous', null, false),
  ('Urgences 24h', null, true),
  ('Hôpitaux', 'hopital', false),
  ('Cliniques', 'clinique', false),
  ('Centres de santé', 'centre_sante', false),
  ('Laboratoires', 'laboratoire', false),
  ('Maternités', 'maternite', false),
];

const _degradeSante = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFF0EA5E9), Color(0xFF0369A1), Color(0xFF0C4A6E)],
);

IconData _iconeType(String type) => switch (type) {
      'hopital' => Icons.local_hospital_outlined,
      'clinique' => Icons.medical_services_outlined,
      'laboratoire' => Icons.biotech_outlined,
      'maternite' => Icons.child_friendly_outlined,
      _ => Icons.health_and_safety_outlined,
    };

class EcranSante extends StatefulWidget {
  const EcranSante({super.key});

  @override
  State<EcranSante> createState() => _EcranSanteState();
}

class _EcranSanteState extends State<EcranSante> {
  int _filtre = 0;
  List<Etablissement>? _etablissements;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() {
      _erreur = null;
      _etablissements = null;
    });
    final (_, type, urgences) = _filtres[_filtre];
    try {
      final liste = await api.etablissements(await positionActuelle(), type: type, urgences: urgences);
      if (mounted) setState(() => _etablissements = liste);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      _EnTete(),
      SizedBox(
        height: 56,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          itemCount: _filtres.length,
          separatorBuilder: (_, _) => const SizedBox(width: 6),
          itemBuilder: (_, i) => ChoiceChip(
            label: Text(tr(_filtres[i].$1)),
            selected: _filtre == i,
            showCheckmark: false,
            onSelected: (_) {
              setState(() => _filtre = i);
              _charger();
            },
          ),
        ),
      ),
      Expanded(child: _contenu()),
    ]);
  }

  Widget _contenu() {
    if (_erreur != null) {
      return EtatIllustre(illustration: 'hors_ligne', titre: tr('Connexion impossible'), texte: _erreur, action: _charger);
    }
    final liste = _etablissements;
    if (liste == null) return const Center(child: CircularProgressIndicator());
    if (liste.isEmpty) {
      return EtatIllustre(illustration: 'recherche_vide', titre: tr('Aucun établissement dans cette catégorie'));
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        itemCount: liste.length + 1,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, i) {
          if (i == 0) return const _BandeauUrgence();
          return _CarteEtablissement(etablissement: liste[i - 1]);
        },
      ),
    );
  }
}

class _EnTete extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: _degradeSante,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      padding: EdgeInsets.fromLTRB(20, MediaQuery.paddingOf(context).top + 20, 12, 20),
      child: Stack(clipBehavior: Clip.none, children: [
        const Positioned(right: -6, bottom: -10, child: Illustration('hopital', hauteur: 100)),
        Row(children: [
          SizedBox(
            width: 180,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('Annuaire\nsanté'),
                  style: TextStyle(color: Colors.white, fontSize: 26, height: 1.1,
                      fontWeight: FontWeight.w800, letterSpacing: -0.5)),
              SizedBox(height: 8),
              Text(tr('Hôpitaux, cliniques, laboratoires près de vous.'),
                  style: TextStyle(color: Color(0xCCFFFFFF), fontSize: 13.5)),
            ]),
          ),
        ]),
      ]),
    );
  }
}

class _BandeauUrgence extends StatelessWidget {
  const _BandeauUrgence();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Row(children: [
        Icon(Icons.emergency_outlined, color: Couleurs.rouge),
        SizedBox(width: 12),
        Expanded(
          child: Text(
            tr('Urgence vitale ? Rendez-vous immédiatement à l\'hôpital le plus proche ouvert 24h/24, ou appelez-le en route.'),
            style: TextStyle(color: Color(0xFF991B1B), fontSize: 13, height: 1.35),
          ),
        ),
      ]),
    );
  }
}

class _CarteEtablissement extends StatelessWidget {
  const _CarteEtablissement({required this.etablissement});

  final Etablissement etablissement;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final e = etablissement;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            IconeTeintee(_iconeType(e.type), couleur: const Color(0xFF0369A1), taille: 48),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e.nom, style: theme.textTheme.titleMedium),
                const SizedBox(height: 2),
                Text(
                  [
                    tr(e.typeLibelle),
                    if (e.distanceKm != null) formatDistance(e.distanceKm!),
                    if (e.quartier.isNotEmpty) e.quartier,
                  ].join(' · '),
                  style: theme.textTheme.bodySmall,
                ),
                if (e.urgences24h) ...[
                  const SizedBox(height: 6),
                  Pastille(tr('Urgences 24h/24'), couleur: Couleurs.rouge, icone: Icons.emergency_outlined),
                ],
              ]),
            ),
          ]),
          if (e.services.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(e.services, style: theme.textTheme.bodySmall?.copyWith(color: Couleurs.texte)),
          ],
          const SizedBox(height: 12),
          Row(children: [
            if (e.telephone.isNotEmpty) ...[
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0369A1)),
                  onPressed: () => appeler(context, e.telephone),
                  icon: const Icon(Icons.call, size: 18),
                  label: Text(tr('Appeler')),
                ),
              ),
              const SizedBox(width: 10),
            ],
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => itineraire(context, e.lat, e.lng, nom: e.nom),
                icon: const Icon(Icons.directions_outlined, size: 18),
                label: Text(tr('Itinéraire')),
              ),
            ),
          ]),
        ]),
      ),
    );
  }
}
