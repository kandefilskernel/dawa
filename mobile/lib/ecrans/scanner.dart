import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../langue.dart';
import '../api.dart';
import '../theme.dart';
import 'resultats.dart';

/// Ouvre le scanner ; si le code correspond à un médicament, affiche directement les pharmacies.
Future<void> scannerBoite(BuildContext context) async {
  final code = await Navigator.of(context).push<String>(
    MaterialPageRoute(builder: (_) => const EcranScanner()),
  );
  if (code == null || !context.mounted) return;
  final messager = ScaffoldMessenger.of(context);
  try {
    final medicament = await api.medicamentParCodeBarres(code);
    if (!context.mounted) return;
    if (medicament == null) {
      messager.showSnackBar(SnackBar(
        content: Text(tr('Code {code} inconnu. Tapez plutôt le nom du médicament.', {'code': code})),
      ));
      return;
    }
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => EcranResultats(medicament: medicament)));
  } on ApiException catch (e) {
    messager.showSnackBar(SnackBar(content: Text(e.message)));
  }
}

/// Scanner de code-barres (renvoie le code lu via Navigator.pop).
class EcranScanner extends StatefulWidget {
  const EcranScanner({super.key, this.titre = 'Scanner la boîte'});

  final String titre;

  @override
  State<EcranScanner> createState() => _EcranScannerState();
}

class _EcranScannerState extends State<EcranScanner> {
  final _controleur = MobileScannerController(
    formats: const [
      BarcodeFormat.ean13, BarcodeFormat.ean8, BarcodeFormat.upcA,
      BarcodeFormat.code128, BarcodeFormat.dataMatrix, BarcodeFormat.qrCode,
    ],
  );
  bool _termine = false;

  @override
  void dispose() {
    _controleur.dispose();
    super.dispose();
  }

  void _surDetection(BarcodeCapture capture) {
    if (_termine) return;
    final code = capture.barcodes.map((b) => b.rawValue).whereType<String>().firstOrNull;
    if (code == null || code.isEmpty) return;
    _termine = true;
    Navigator.of(context).pop(code);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(tr(widget.titre), style: const TextStyle(color: Colors.white)),
        actions: [
          IconButton(
            tooltip: tr('Lampe'),
            icon: const Icon(Icons.flashlight_on_outlined),
            onPressed: () => _controleur.toggleTorch(),
          ),
        ],
      ),
      body: Stack(children: [
        MobileScanner(
          controller: _controleur,
          onDetect: _surDetection,
          errorBuilder: (context, erreur) => Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Text(
                tr('Caméra indisponible. Autorisez l\'accès à la caméra dans les réglages du téléphone.'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ),
        ),
        // Cadre de visée
        Center(
          child: Container(
            width: 260,
            height: 170,
            decoration: BoxDecoration(
              border: Border.all(color: Couleurs.ambre, width: 3),
              borderRadius: BorderRadius.circular(20),
            ),
          ),
        ),
        Positioned(
          left: 24,
          right: 24,
          bottom: 48,
          child: Text(
            tr('Placez le code-barres de la boîte dans le cadre'),
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ),
      ]),
    );
  }
}
