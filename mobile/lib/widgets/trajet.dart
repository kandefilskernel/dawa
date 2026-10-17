import 'package:flutter/material.dart';

import '../langue.dart';
import '../models.dart';
import '../theme.dart';
import 'pharmacie_carte.dart';

extension ModeTrajetAffichage on ModeTrajet {
  IconData get icone => switch (this) {
        ModeTrajet.pied => Icons.directions_walk,
        ModeTrajet.moto => Icons.two_wheeler,
        ModeTrajet.voiture => Icons.directions_car_outlined,
      };

  /// « à pied », « à moto », « en voiture » : fin de phrase après une durée.
  String get maniere => switch (this) {
        ModeTrajet.pied => tr('à pied'),
        ModeTrajet.moto => tr('à moto'),
        ModeTrajet.voiture => tr('en voiture'),
      };

  String get libelle => switch (this) {
        ModeTrajet.pied => tr('À pied'),
        ModeTrajet.moto => tr('Moto'),
        ModeTrajet.voiture => tr('Voiture'),
      };
}

/// 8 min, 1 h 05, 2 j.
String formatDuree(int minutes) {
  if (minutes < 60) return tr('{n} min', {'n': minutes});
  if (minutes < 24 * 60) {
    final h = minutes ~/ 60, m = minutes % 60;
    return m == 0 ? '$h h' : '$h h ${m.toString().padLeft(2, '0')}';
  }
  return tr('{n} j', {'n': (minutes / (24 * 60)).round()});
}

/// Phrase principale d'un résultat : « Disponible en 8 min à moto », ou l'attente si c'est fermé.
String phraseAcces(Acces acces, ModeTrajet mode) {
  final delai = acces.delaiMin[mode];
  if (delai == null) return tr('Fermée cette semaine');
  if (acces.ouverte == false) {
    return tr('Fermée : disponible dans {duree} (à l\'ouverture)', {'duree': formatDuree(delai)});
  }
  return tr('Disponible en {duree} {mode}', {'duree': formatDuree(delai), 'mode': mode.maniere});
}

/// Bandeau sous le nom de la pharmacie : délai, trajet par la route, autres modes.
class LigneAcces extends StatelessWidget {
  const LigneAcces({super.key, required this.acces, required this.mode});

  final Acces acces;
  final ModeTrajet mode;

  @override
  Widget build(BuildContext context) {
    final fermee = acces.ouverte == false;
    final couleur = fermee ? const Color(0xFFB45309) : Couleurs.emeraudeFonce;
    final trajet = acces.trajets[mode];
    final autres = ModeTrajet.values.where((m) => m != mode && acces.trajets[m] != null);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(fermee ? Icons.lock_clock_outlined : mode.icone, size: 18, color: couleur),
        const SizedBox(width: 6),
        Expanded(
          child: Text(phraseAcces(acces, mode),
              style: TextStyle(color: couleur, fontWeight: FontWeight.w800, fontSize: 14.5)),
        ),
      ]),
      if (trajet != null) ...[
        const SizedBox(height: 3),
        Text.rich(
          TextSpan(children: [
            TextSpan(
              text: trajet.parLaRoute
                  ? tr('{distance} par la route', {'distance': formatDistance(trajet.distanceKm)})
                  : tr('environ {distance} (estimation)', {'distance': formatDistance(trajet.distanceKm)}),
            ),
            for (final m in autres)
              TextSpan(text: '  ·  ${formatDuree(acces.trajets[m]!.minutes)} ${m.maniere}'),
          ]),
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    ]);
  }
}

/// Choix du mode de trajet : à pied, moto, voiture.
class SelecteurMode extends StatelessWidget {
  const SelecteurMode({super.key, required this.mode, required this.onChanged});

  final ModeTrajet mode;
  final ValueChanged<ModeTrajet> onChanged;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<ModeTrajet>(
      showSelectedIcon: false,
      style: SegmentedButton.styleFrom(
        selectedBackgroundColor: Couleurs.emeraude,
        selectedForegroundColor: Colors.white,
        backgroundColor: Colors.white,
        side: const BorderSide(color: Couleurs.bordure),
        visualDensity: VisualDensity.compact,
      ),
      segments: [
        for (final m in ModeTrajet.values)
          ButtonSegment(value: m, icon: Icon(m.icone, size: 18), label: Text(m.libelle)),
      ],
      selected: {mode},
      onSelectionChanged: (s) => onChanged(s.first),
    );
  }
}
