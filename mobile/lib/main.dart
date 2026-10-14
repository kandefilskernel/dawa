import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'ecrans/accueil.dart';
import 'ecrans/choix_langue.dart';
import 'langue.dart';
import 'rappels.dart';
import 'stockage.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await stockage.init();
  await langues.init();
  await rappels.init();
  // Les notifications déjà programmées sont réécrites dans la nouvelle langue.
  langues.courante.addListener(rappels.reprogrammer);
  runApp(const DawaApp());
}

class DawaApp extends StatelessWidget {
  const DawaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Langue>(
      valueListenable: langues.courante,
      builder: (_, langue, _) => MaterialApp(
        title: 'Dawa',
        debugShowCheckedModeBanner: false,
        theme: construireTheme(),
        // Boutons, calendriers et horloges d'Android dans la langue choisie.
        locale: langue.locale,
        supportedLocales: [for (final l in Langue.values) l.locale],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        // Nouvelle clé à chaque changement de langue : tous les écrans sont reconstruits.
        home: KeyedSubtree(
          key: ValueKey(langue),
          child: langues.aChoisir ? const EcranChoixLangue() : const Accueil(),
        ),
      ),
    );
  }
}
