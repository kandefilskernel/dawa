import 'package:dawa/ecrans/choix_langue.dart';
import 'package:dawa/langue.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await langues.init();
    langues.courante.value = Langue.fr;
  });

  test('tr traduit et remplace les variables', () {
    expect(tr('Rechercher'), 'Rechercher');
    expect(tr('Expire dans {duree}', {'duree': '1 h'}), 'Expire dans 1 h');

    langues.courante.value = Langue.sw;
    expect(tr('Rechercher'), 'Tafuta');
    expect(tr('Expire dans {duree}', {'duree': '1 h'}), 'Inaisha baada ya 1 h');

    langues.courante.value = Langue.en;
    expect(tr('Rechercher'), 'Search');
    expect(tr('Texte inconnu'), 'Texte inconnu', reason: 'repli sur le français');
  });

  testWidgets('premier lancement : choisir sa langue l\'enregistre', (tester) async {
    expect(langues.aChoisir, isTrue);
    await tester.pumpWidget(const MaterialApp(home: EcranChoixLangue()));

    // Les trois langues sont proposées, chacune écrite dans sa propre langue.
    expect(find.text('Français'), findsOneWidget);
    expect(find.text('Kiswahili'), findsOneWidget);
    expect(find.text('English'), findsOneWidget);
    expect(find.text('Chagua lugha yako'), findsOneWidget);

    await tester.tap(find.text('Kiswahili'));
    await tester.pump();

    expect(langues.courante.value, Langue.sw);
    expect(langues.aChoisir, isFalse);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('langue'), 'sw');
  });
}
