import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import '../widgets/reservation_sheet.dart';
import '../widgets/image_medicament.dart';

void ouvrirFichePharmacie(BuildContext context, Pharmacie pharmacie) {
  Navigator.of(context).push(MaterialPageRoute(builder: (_) => FichePharmacie(pharmacie: pharmacie)));
}

class FichePharmacie extends StatefulWidget {
  const FichePharmacie({super.key, required this.pharmacie});

  final Pharmacie pharmacie;

  @override
  State<FichePharmacie> createState() => _FichePharmacieState();
}

class _FichePharmacieState extends State<FichePharmacie> {
  final _filtre = TextEditingController();
  List<ProduitEnStock>? _produits;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
    _filtre.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _filtre.dispose();
    super.dispose();
  }

  Future<void> _charger() async {
    setState(() => _erreur = null);
    try {
      final produits = await api.produitsPharmacie(widget.pharmacie.id);
      if (mounted) setState(() => _produits = produits);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  List<ProduitEnStock> get _produitsFiltres {
    final terme = _filtre.text.trim().toLowerCase();
    final produits = _produits ?? [];
    if (terme.isEmpty) return produits;
    return produits
        .where((p) => '${p.medicament.libelle} ${p.medicament.dci}'.toLowerCase().contains(terme))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.pharmacie;
    final theme = Theme.of(context);
    final produits = _produitsFiltres;

    return Scaffold(
      body: CustomScrollView(slivers: [
        SliverAppBar(
          pinned: true,
          expandedHeight: 210,
          backgroundColor: p.deGarde ? Couleurs.indigoFonce : Couleurs.emeraudeFonce,
          foregroundColor: Colors.white,
          actions: [
            ValueListenableBuilder(
              valueListenable: stockage.favoris,
              builder: (_, _, _) {
                final favori = stockage.estFavori(p.id);
                return IconButton(
                  tooltip: favori ? tr('Retirer des favoris') : tr('Ajouter aux favoris'),
                  icon: Icon(favori ? Icons.favorite : Icons.favorite_border,
                      color: favori ? const Color(0xFFFCA5A5) : Colors.white),
                  onPressed: () => stockage.basculerFavori(p),
                );
              },
            ),
          ],
          flexibleSpace: FlexibleSpaceBar(
            background: Container(
              decoration: BoxDecoration(gradient: p.deGarde ? Couleurs.degradeNuit : Couleurs.degradeMarque),
              padding: EdgeInsets.fromLTRB(20, MediaQuery.paddingOf(context).top + 56, 20, 20),
              child: Stack(children: [
                const Positioned(right: -10, bottom: -10,
                    child: Opacity(opacity: 0.9, child: Illustration('pharmacie', hauteur: 110))),
                Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                  if (p.deGarde) ...[
                    Pastille(tr('De garde'), couleur: Color(0xFFFDE68A), icone: Icons.nightlight_round),
                    const SizedBox(height: 8),
                  ],
                  SizedBox(
                    width: 220,
                    child: Text(p.nom,
                        style: const TextStyle(color: Colors.white, fontSize: 24, height: 1.15,
                            fontWeight: FontWeight.w800, letterSpacing: -0.4)),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    [
                      if (p.quartier.isNotEmpty) p.quartier,
                      if (p.distanceKm != null) formatDistance(p.distanceKm!),
                    ].join(' · '),
                    style: const TextStyle(color: Color(0xD9FFFFFF)),
                  ),
                ]),
              ]),
            ),
          ),
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => appeler(context, p.telephone),
                    icon: const Icon(Icons.call, size: 18),
                    label: Text(tr('Appeler')),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(backgroundColor: Colors.white),
                    onPressed: () => itineraire(context, p.lat, p.lng),
                    icon: const Icon(Icons.directions_outlined, size: 18),
                    label: Text(tr('Itinéraire')),
                  ),
                ),
              ]),
              const SizedBox(height: 16),
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(children: [
                  SizedBox(
                    height: 150,
                    child: IgnorePointer(
                      child: FlutterMap(
                        options: MapOptions(initialCenter: LatLng(p.lat, p.lng), initialZoom: 15.5),
                        children: [
                          TileLayer(
                            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                            userAgentPackageName: 'cd.dawa.dawa',
                          ),
                          MarkerLayer(markers: [
                            Marker(
                              point: LatLng(p.lat, p.lng),
                              width: 44,
                              height: 44,
                              alignment: Alignment.topCenter,
                              child: Icon(Icons.location_on, size: 44,
                                  color: p.deGarde ? Couleurs.indigo : Couleurs.emeraude),
                            ),
                          ]),
                        ],
                      ),
                    ),
                  ),
                  _Info(icone: Icons.place_outlined, texte: p.adresse),
                  if (p.horaires.isNotEmpty) _Info(icone: Icons.schedule, texte: p.horaires),
                  if (p.telephone.isNotEmpty) _Info(icone: Icons.phone_outlined, texte: p.telephone),
                  const SizedBox(height: 14),
                ]),
              ),
              const SizedBox(height: 24),
              Row(children: [
                Text(tr('Produits disponibles'), style: theme.textTheme.titleMedium),
                const SizedBox(width: 8),
                if (_produits != null)
                  Pastille('${_produits!.length}', couleur: Couleurs.emeraude),
              ]),
              const SizedBox(height: 10),
              TextField(
                controller: _filtre,
                decoration: InputDecoration(
                  hintText: tr('Filtrer les produits'),
                  prefixIcon: const Icon(Icons.search),
                  isDense: true,
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: Couleurs.bordure),
                  ),
                ),
              ),
              const SizedBox(height: 10),
            ]),
          ),
        ),
        if (_erreur != null)
          SliverToBoxAdapter(
            child: EtatIllustre(
              illustration: 'hors_ligne',
              titre: tr('Produits indisponibles'),
              texte: _erreur,
              action: _charger,
            ),
          )
        else if (_produits == null)
          const SliverToBoxAdapter(
            child: Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
          )
        else if (produits.isEmpty)
          SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Text(tr('Aucun produit ne correspond.'), textAlign: TextAlign.center),
            ),
          )
        else
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
            sliver: SliverList.separated(
              itemCount: produits.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _LigneProduit(pharmacie: p, produit: produits[i]),
            ),
          ),
      ]),
    );
  }
}

class _Info extends StatelessWidget {
  const _Info({required this.icone, required this.texte});

  final IconData icone;
  final String texte;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(children: [
        Icon(icone, size: 18, color: Couleurs.emeraude),
        const SizedBox(width: 10),
        Expanded(child: Text(texte)),
      ]),
    );
  }
}

class _LigneProduit extends StatelessWidget {
  const _LigneProduit({required this.pharmacie, required this.produit});

  final Pharmacie pharmacie;
  final ProduitEnStock produit;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final m = produit.medicament;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
        child: Row(children: [
          GestureDetector(
            onTap: () => ouvrirImageMedicament(context, m),
            child: ImageMedicament(m, taille: 52),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.libelle, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              Row(children: [
                if (produit.prix != null)
                  Text(formatPrix(produit.prix!),
                      style: const TextStyle(color: Couleurs.emeraudeFonce, fontWeight: FontWeight.w800)),
                if (m.ordonnanceRequise) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.receipt_long, size: 14, color: Couleurs.rouge),
                ],
                if (!produit.confirme) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.schedule, size: 14, color: Color(0xFFB45309)),
                ],
              ]),
            ]),
          ),
          FilledButton.tonal(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 38), padding: const EdgeInsets.symmetric(horizontal: 14)),
            onPressed: () => ouvrirReservation(context, pharmacie: pharmacie, medicament: m, prix: produit.prix),
            child: Text(tr('Réserver')),
          ),
        ]),
      ),
    );
  }
}
