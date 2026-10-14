import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../langue.dart';
import '../theme.dart';

final _voix = SpeechToText();

/// Fin de l'écoute (silence, délai écoulé ou erreur) signalée par le téléphone.
final _ecouteTerminee = ValueNotifier<int>(0);

/// Noms souvent dits : aident la reconnaissance vocale à les comprendre.
const _nomsFrequents = [
  'Paracétamol', 'Doliprane', 'Amoxicilline', 'Coartem', 'Ibuprofène', 'Flagyl', 'Quinine', 'SRO',
];

/// Ouvre l'écoute et renvoie le nom dicté (null si annulé ou rien compris).
/// La reconnaissance utilise la langue choisie dans l'app si le téléphone la connaît.
Future<String?> dicterNomMedicament(BuildContext context) async {
  final messager = ScaffoldMessenger.of(context);
  final pret = await _voix.initialize(
    onStatus: (statut) {
      if (statut == SpeechToText.doneStatus) _ecouteTerminee.value++;
    },
    onError: (_) => _ecouteTerminee.value++,
  );
  if (!pret) {
    messager.showSnackBar(SnackBar(
      content: Text(tr('La recherche à la voix n\'est pas disponible sur ce téléphone. Autorisez le micro ou tapez le nom.')),
    ));
    return null;
  }
  if (!context.mounted) return null;
  return showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (_) => const _Ecoute(),
  );
}

Future<String?> _localeVoix() async {
  final code = langues.courante.value.name;
  final disponibles = await _voix.locales();
  for (final l in disponibles) {
    if (l.localeId.toLowerCase().startsWith(code)) return l.localeId;
  }
  return null; // langue du téléphone par défaut
}

class _Ecoute extends StatefulWidget {
  const _Ecoute();

  @override
  State<_Ecoute> createState() => _EcouteState();
}

class _EcouteState extends State<_Ecoute> {
  String _entendu = '';
  bool _ecoute = false;

  @override
  void initState() {
    super.initState();
    _ecouteTerminee.addListener(_surFin);
    _demarrer();
  }

  @override
  void dispose() {
    _ecouteTerminee.removeListener(_surFin);
    _voix.stop();
    super.dispose();
  }

  void _surFin() {
    if (mounted) setState(() => _ecoute = false);
  }

  Future<void> _demarrer() async {
    final locale = await _localeVoix();
    if (!mounted) return;
    setState(() {
      _entendu = '';
      _ecoute = true;
    });
    await _voix.listen(
      onResult: (r) {
        if (!mounted) return;
        setState(() => _entendu = r.recognizedWords);
        if (r.finalResult) {
          setState(() => _ecoute = false);
          if (r.recognizedWords.trim().isNotEmpty) Navigator.of(context).pop(r.recognizedWords.trim());
        }
      },
      listenOptions: SpeechListenOptions(
        localeId: locale,
        listenFor: const Duration(seconds: 10),
        pauseFor: const Duration(seconds: 3),
        listenMode: ListenMode.search,
        cancelOnError: true,
        contextualPhrases: _nomsFrequents,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(_ecoute ? tr('Dites le nom du médicament') : tr('Je n\'ai pas compris'),
              style: theme.textTheme.titleLarge, textAlign: TextAlign.center),
          const SizedBox(height: 20),
          Semantics(
            button: true,
            label: _ecoute ? tr('Arrêter l\'écoute') : tr('Parler à nouveau'),
            child: GestureDetector(
              onTap: _ecoute ? () => _voix.stop() : _demarrer,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: _ecoute ? 104 : 88,
                height: _ecoute ? 104 : 88,
                decoration: BoxDecoration(
                  color: _ecoute ? Couleurs.emeraude : Couleurs.menthe,
                  shape: BoxShape.circle,
                  boxShadow: _ecoute ? ombreDouce : null,
                ),
                child: Icon(Icons.mic, size: 48, color: _ecoute ? Colors.white : Couleurs.emeraudeFonce),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            _entendu.isEmpty ? (_ecoute ? tr('Je vous écoute…') : tr('Touchez le micro pour réessayer.')) : _entendu,
            style: theme.textTheme.titleMedium?.copyWith(color: _entendu.isEmpty ? Couleurs.texteDoux : null),
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    );
  }
}
