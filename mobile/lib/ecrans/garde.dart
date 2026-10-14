import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../position.dart';
import '../stockage.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';

class EcranGarde extends StatefulWidget {
  const EcranGarde({super.key});

  @override
  State<EcranGarde> createState() => _EcranGardeState();
}

class _EcranGardeState extends State<EcranGarde> {
  List<Pharmacie>? _pharmacies;
  String? _erreur;

  /// Date de la liste affichée quand elle vient du cache (mode hors ligne).
  DateTime? _dateCache;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() => _erreur = null);
    try {
      final pharmacies = await api.pharmaciesDeGarde(await positionActuelle());
      await stockage.sauverGardes(pharmacies);
      if (mounted) {
        setState(() {
          _pharmacies = pharmacies;
          _dateCache = null;
        });
      }
    } on ApiException catch (e) {
      final cache = stockage.gardesEnCache;
      if (!mounted) return;
      setState(() {
        _erreur = e.message;
        if (cache != null) {
          _pharmacies = cache.pharmacies;
          _dateCache = cache.date;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _EnTeteNuit(nombre: _pharmacies?.length),
        Expanded(child: _contenu()),
      ],
    );
  }

  Widget _contenu() {
    if (_erreur != null && _pharmacies == null) {
      return EtatIllustre(
        illustration: 'hors_ligne',
        titre: tr('Connexion impossible'),
        texte: _erreur,
        action: _charger,
      );
    }
    final pharmacies = _pharmacies;
    if (pharmacies == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (pharmacies.isEmpty) {
      return EtatIllustre(
        illustration: 'garde',
        titre: tr('Aucune garde enregistrée'),
        texte: tr('Le planning de garde n\'a pas encore été publié pour aujourd\'hui.'),
        libelleAction: tr('Actualiser'),
        action: _charger,
      );
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
        itemCount: pharmacies.length + (_dateCache != null ? 1 : 0),
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, i) {
          if (_dateCache != null) {
            if (i == 0) return _BandeauHorsLigne(date: _dateCache!);
            i--;
          }
          return PharmacieCarte(pharmacie: pharmacies[i]);
        },
      ),
    );
  }
}

class _EnTeteNuit extends StatelessWidget {
  const _EnTeteNuit({required this.nombre});

  final int? nombre;

  @override
  Widget build(BuildContext context) {
    final haut = MediaQuery.paddingOf(context).top;
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: Couleurs.degradeNuit,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      padding: EdgeInsets.fromLTRB(20, haut + 20, 12, 22),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          const Positioned(
            right: -4,
            bottom: -8,
            child: Illustration('garde', hauteur: 96),
          ),
          // La Row occupe toute la largeur, pour que l'illustration se cale à droite.
          Row(
            children: [
              SizedBox(
                width: 190,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tr('Pharmacies\nde garde'),
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 26,
                        height: 1.1,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      tr('Ouvertes en dehors des heures habituelles.'),
                      style: TextStyle(
                        color: Color(0xCCFFFFFF),
                        fontSize: 13.5,
                      ),
                    ),
                    if (nombre != null && nombre! > 0) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 5,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFDE68A),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: Color(0xFF16A34A),
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              nombre! > 1 ? tr('{n} ouvertes maintenant', {'n': nombre}) : tr('{n} ouverte maintenant', {'n': nombre}),
                              style: const TextStyle(
                                color: Couleurs.indigoFonce,
                                fontWeight: FontWeight.w800,
                                fontSize: 12.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BandeauHorsLigne extends StatelessWidget {
  const _BandeauHorsLigne({required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    String deux(int n) => n.toString().padLeft(2, '0');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Couleurs.ambreClair, borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        const Icon(Icons.cloud_off_outlined, color: Color(0xFFB45309), size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            tr('Hors ligne : liste enregistrée le {date} à {heure}. Tirez vers le bas pour actualiser.', {
              'date': '${deux(date.day)}/${deux(date.month)}',
              'heure': '${deux(date.hour)}h${deux(date.minute)}',
            }),
            style: const TextStyle(color: Color(0xFF92400E), fontSize: 12.5),
          ),
        ),
      ]),
    );
  }
}
