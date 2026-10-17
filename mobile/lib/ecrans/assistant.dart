import 'package:flutter/material.dart';

import '../api.dart';
import '../langue.dart';
import '../models.dart';
import '../position.dart';
import '../theme.dart';
import '../widgets/communs.dart';
import '../widgets/pharmacie_carte.dart';
import '../widgets/reservation_sheet.dart';
import '../widgets/trajet.dart';

/// « J'ai besoin d'Amoxicilline, je suis à pied, c'est urgent » → la pharmacie et l'action les plus rapides.
class EcranAssistant extends StatefulWidget {
  const EcranAssistant({super.key});

  @override
  State<EcranAssistant> createState() => _EcranAssistantState();
}

class _Echange {
  _Echange(this.question);

  final String question;
  ReponseAssistant? reponse;
  String? erreur;
}

class _EcranAssistantState extends State<EcranAssistant> {
  final _saisie = TextEditingController();
  final _defilement = ScrollController();
  final _echanges = <_Echange>[];
  bool _envoi = false;

  @override
  void dispose() {
    _saisie.dispose();
    _defilement.dispose();
    super.dispose();
  }

  Future<void> _envoyer([String? texte]) async {
    final message = (texte ?? _saisie.text).trim();
    if (message.length < 3 || _envoi) return;
    final echange = _Echange(message);
    setState(() {
      _echanges.add(echange);
      _envoi = true;
      _saisie.clear();
    });
    _defilerEnBas();
    try {
      final position = await positionActuelle();
      echange.reponse = await api.demanderAssistant(message, position);
    } on ApiException catch (e) {
      echange.erreur = e.message;
    } finally {
      if (mounted) setState(() => _envoi = false);
      _defilerEnBas();
    }
  }

  void _defilerEnBas() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_defilement.hasClients) {
          _defilement.animateTo(_defilement.position.maxScrollExtent,
              duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
        }
      });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(tr('Assistant Uzima'))),
      body: Column(children: [
        Expanded(
          child: ListView(controller: _defilement, padding: const EdgeInsets.fromLTRB(16, 8, 16, 16), children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(gradient: Couleurs.degradeMarque, borderRadius: BorderRadius.circular(24)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('Obtenez votre médicament au plus vite'),
                    style: theme.textTheme.titleMedium?.copyWith(color: Colors.white, fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Text(
                  tr('Dites ce qu\'il vous faut et comment vous vous déplacez : l\'assistant choisit la pharmacie la plus rapide, avec les stocks et les trajets réels.'),
                  style: const TextStyle(color: Color(0xD9FFFFFF), fontSize: 13, height: 1.35),
                ),
              ]),
            ),
            if (_echanges.isEmpty) ...[
              const SizedBox(height: 16),
              Text(tr('Exemples'), style: theme.textTheme.titleSmall),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final exemple in [
                  tr('J\'ai besoin d\'Amoxicilline, je suis à pied, c\'est urgent'),
                  tr('Paracétamol sirop, je suis à moto'),
                  tr('Coartem livré à la maison'),
                ])
                  ActionChip(label: Text(exemple), onPressed: () => _envoyer(exemple)),
              ]),
            ],
            for (final e in _echanges) ...[
              const SizedBox(height: 14),
              Align(alignment: Alignment.centerRight, child: _Bulle(e.question)),
              const SizedBox(height: 10),
              if (e.erreur != null)
                Text(e.erreur!, style: const TextStyle(color: Couleurs.rouge, fontWeight: FontWeight.w600))
              else if (e.reponse == null)
                const _Reflexion()
              else
                _Reponse(reponse: e.reponse!),
            ],
            const SizedBox(height: 12),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.info_outline, size: 15, color: Couleurs.texteDoux),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  tr('L\'assistant vous aide à trouver un médicament, il ne donne pas d\'avis médical. En cas d\'urgence, allez à l\'hôpital.'),
                  style: theme.textTheme.bodySmall,
                ),
              ),
            ]),
          ]),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _saisie,
                  maxLength: 500,
                  minLines: 1,
                  maxLines: 3,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _envoyer(),
                  decoration: InputDecoration(
                    hintText: tr('Ex. Amoxicilline, je suis à pied'),
                    counterText: '',
                    fillColor: Colors.white,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                tooltip: tr('Envoyer'),
                onPressed: _envoi ? null : _envoyer,
                icon: const Icon(Icons.send),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}

class _Bulle extends StatelessWidget {
  const _Bulle(this.texte);

  final String texte;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 320),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Couleurs.emeraude,
          borderRadius: BorderRadius.circular(18).copyWith(bottomRight: const Radius.circular(4)),
        ),
        child: Text(texte, style: const TextStyle(color: Colors.white)),
      );
}

class _Reflexion extends StatelessWidget {
  const _Reflexion();

  @override
  Widget build(BuildContext context) => Row(children: [
        const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
        const SizedBox(width: 10),
        Text(tr('Je regarde les stocks et les trajets…'), style: Theme.of(context).textTheme.bodySmall),
      ]);
}

/// Phrase de la réponse : celle de l'IA, sinon composée ici à partir des données (dans la langue choisie).
String texteReponse(ReponseAssistant r) {
  if (r.reponse.isNotEmpty) return r.reponse;
  if (r.situation == 'medicament_inconnu') {
    return tr('Je n\'ai pas reconnu le médicament. Écrivez son nom, par exemple « Amoxicilline ».');
  }
  final rec = r.recommandation;
  if (rec == null) {
    return tr('{medicament} n\'est signalé en stock dans aucune pharmacie proche. Créez une alerte depuis la recherche : vous serez prévenu dès qu\'il est disponible.',
        {'medicament': r.medicament?.nomCommercial ?? ''});
  }
  final prix = rec.prix == null ? '' : ' (${formatPrix(rec.prix!)})';
  final livraison = rec.livraison;
  if (r.action == 'se_faire_livrer' && livraison?.minutes != null) {
    return tr('Le plus rapide : vous faire livrer par {pharmacie}{prix}, chez vous dans environ {duree}, livraison {frais}.', {
      'pharmacie': rec.pharmacie.nom,
      'prix': prix,
      'duree': formatDuree(livraison!.minutes!),
      'frais': formatPrix(livraison.frais ?? 0),
    });
  }
  final acces = rec.acces;
  final debut = tr('Le plus rapide : {pharmacie}{prix}.', {'pharmacie': rec.pharmacie.nom, 'prix': prix});
  final delai = acces == null ? '' : ' ${phraseAcces(acces, r.mode)}.';
  return '$debut$delai ${tr('Réservez : la pharmacie vous le met de côté.')}';
}

class _Reponse extends StatelessWidget {
  const _Reponse({required this.reponse});

  final ReponseAssistant reponse;

  @override
  Widget build(BuildContext context) {
    final r = reponse;
    final rec = r.recommandation;
    final theme = Theme.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (r.orienterMedecin) ...[
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFFFEE2E2), borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            const Icon(Icons.local_hospital, color: Couleurs.rouge),
            const SizedBox(width: 10),
            Expanded(
              child: Text(tr('Ces signes demandent un médecin : allez tout de suite à l\'hôpital ou dans un centre de santé.'),
                  style: const TextStyle(color: Color(0xFF991B1B), fontWeight: FontWeight.w600)),
            ),
          ]),
        ),
        const SizedBox(height: 10),
      ],
      Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const IconeTeintee(Icons.assistant_outlined, taille: 36),
            const SizedBox(width: 10),
            Expanded(child: Text(texteReponse(r), style: theme.textTheme.bodyMedium?.copyWith(height: 1.4))),
          ]),
        ),
      ),
      if (rec != null) ...[
        const SizedBox(height: 10),
        if (r.action == 'se_faire_livrer' && rec.pharmacie.livraison)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Couleurs.indigo),
              onPressed: () => ouvrirReservation(context,
                  pharmacie: rec.pharmacie, medicament: rec.medicament, prix: rec.prix, livraison: true),
              icon: const Icon(Icons.two_wheeler),
              label: Text(tr('Me faire livrer')),
            ),
          ),
        PharmacieCarte(
          pharmacie: rec.pharmacie,
          resultat: rec,
          medicamentRecherche: r.medicament,
          plusRapide: true,
          mode: r.mode,
        ),
      ],
      if (r.autres.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text(tr('Autres possibilités'), style: theme.textTheme.titleSmall),
        for (final autre in r.autres)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: PharmacieCarte(pharmacie: autre.pharmacie, resultat: autre, medicamentRecherche: r.medicament, mode: r.mode),
          ),
      ],
    ]);
  }
}
