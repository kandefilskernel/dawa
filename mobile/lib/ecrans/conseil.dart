import 'package:flutter/material.dart';

import '../langue.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/communs.dart';

/// « Demander à un pharmacien » : questions simples, réponses des pharmaciens partenaires.
class EcranConseil extends StatefulWidget {
  const EcranConseil({super.key});

  @override
  State<EcranConseil> createState() => _EcranConseilState();
}

class _EcranConseilState extends State<EcranConseil> {
  final _texte = TextEditingController();
  List<Question>? _questions;
  String? _erreur;
  bool _envoi = false;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  @override
  void dispose() {
    _texte.dispose();
    super.dispose();
  }

  Future<void> _charger() async {
    try {
      final questions = await api.questions();
      if (mounted) setState(() => _questions = questions);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erreur = e.message);
    }
  }

  Future<void> _poser() async {
    final texte = _texte.text.trim();
    if (texte.isEmpty) return;
    setState(() => _envoi = true);
    final messager = ScaffoldMessenger.of(context);
    try {
      await api.poserQuestion(texte);
      _texte.clear();
      if (mounted) FocusScope.of(context).unfocus();
      messager.showSnackBar(SnackBar(content: Text(tr('Question envoyée. Un pharmacien va vous répondre.'))));
      await _charger();
    } on ApiException catch (e) {
      messager.showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _envoi = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final questions = _questions;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Demander à un pharmacien'))),
      body: RefreshIndicator(
        onRefresh: _charger,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 32), children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF2F2),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFFECACA)),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.emergency_outlined, color: Couleurs.rouge),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  tr('Urgence (difficulté à respirer, douleur forte, perte de connaissance, enfant très fiévreux) : allez immédiatement à l\'hôpital. Ce service ne remplace pas une consultation.'),
                  style: TextStyle(color: Color(0xFF991B1B), fontSize: 13, height: 1.35),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text(tr('Votre question'), style: theme.textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(tr('Prise, posologie, interactions, conservation, notice…'), style: theme.textTheme.bodySmall),
                const SizedBox(height: 12),
                TextField(
                  controller: _texte,
                  maxLines: 4,
                  minLines: 3,
                  maxLength: 1000,
                  decoration: InputDecoration(
                    hintText: tr('Ex. Puis-je donner du paracétamol sirop à un enfant de 3 ans ?'),
                    fillColor: Couleurs.fond,
                  ),
                ),
                FilledButton.icon(
                  onPressed: _envoi ? null : _poser,
                  icon: const Icon(Icons.send, size: 18),
                  label: Text(tr('Envoyer')),
                ),
              ]),
            ),
          ),
          const SizedBox(height: 24),
          Text(tr('Mes questions'), style: theme.textTheme.titleMedium),
          const SizedBox(height: 10),
          if (_erreur != null && questions == null)
            EtatIllustre(illustration: 'hors_ligne', titre: tr('Connexion impossible'), texte: _erreur, action: _charger)
          else if (questions == null)
            const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
          else if (questions.isEmpty)
            Text(tr('Vous n\'avez pas encore posé de question.'), style: theme.textTheme.bodySmall)
          else
            for (final q in questions) ...[_CarteQuestion(question: q), const SizedBox(height: 12)],
        ]),
      ),
    );
  }
}

class _CarteQuestion extends StatelessWidget {
  const _CarteQuestion({required this.question});

  final Question question;

  @override
  Widget build(BuildContext context) {
    final q = question;
    final orientee = q.statut == 'orientee';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Pastille(
            tr(q.statutLibelle),
            couleur: !q.estRepondue ? const Color(0xFFB45309) : (orientee ? Couleurs.rouge : Couleurs.emeraude),
            icone: !q.estRepondue ? Icons.hourglass_top : (orientee ? Icons.local_hospital_outlined : Icons.check_circle),
          ),
          const SizedBox(height: 10),
          Text('« ${q.texte} »', style: const TextStyle(fontWeight: FontWeight.w600)),
          if (q.estRepondue) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Couleurs.fond, borderRadius: BorderRadius.circular(12)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.local_pharmacy, size: 16, color: Couleurs.emeraude),
                  const SizedBox(width: 6),
                  Text(q.reponduPar ?? tr('Pharmacien Uzima'),
                      style: const TextStyle(fontWeight: FontWeight.w700, color: Couleurs.emeraudeFonce)),
                ]),
                const SizedBox(height: 6),
                Text(q.reponse, style: const TextStyle(height: 1.4)),
              ]),
            ),
          ],
        ]),
      ),
    );
  }
}
