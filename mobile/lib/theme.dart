import 'package:flutter/material.dart';

/// Palette de la marque Uzima.
abstract final class Couleurs {
  static const emeraude = Color(0xFF0B8F6A);
  static const emeraudeVif = Color(0xFF10B981);
  static const emeraudeFonce = Color(0xFF064E3B);
  static const menthe = Color(0xFFD1FAE5);
  static const menthePale = Color(0xFFECFDF5);
  static const ambre = Color(0xFFF59E0B);
  static const ambreClair = Color(0xFFFEF3C7);
  /// Ambre assez foncé pour porter du texte blanc ou être lu sur fond clair.
  static const ambreFonce = Color(0xFFB45309);
  /// Jaune du petit soleil du logo, lisible sur les dégradés.
  static const soleil = Color(0xFFFCD34D);
  static const indigo = Color(0xFF4338CA);
  static const indigoFonce = Color(0xFF1E1B4B);
  static const ciel = Color(0xFF0369A1);
  static const rouge = Color(0xFFDC2626);
  static const fond = Color(0xFFF3F7F5);
  static const texte = Color(0xFF0F172A);
  static const texteDoux = Color(0xFF475569);
  static const bordure = Color(0xFFE2E8F0);

  static const degradeMarque = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF10B981), Color(0xFF0B8F6A), Color(0xFF065F46)],
  );

  static const degradeNuit = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF4338CA), Color(0xFF312E81), Color(0xFF1E1B4B)],
  );

  static const degradeSante = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0EA5E9), Color(0xFF0369A1), Color(0xFF0C4A6E)],
  );
}

/// Espacements et arrondis communs : les écrans s'alignent sur la même grille de 4.
abstract final class Mesures {
  static const marge = 20.0;
  static const ecart = 12.0;
  static const rayonCarte = 20.0;
  static const rayonBouton = 14.0;
  static const rayonChamp = 16.0;
}

const policeMarque = 'PlusJakartaSans';

const ombreDouce = [
  BoxShadow(color: Color(0x0F064E3B), blurRadius: 24, offset: Offset(0, 8)),
  BoxShadow(color: Color(0x0A000000), blurRadius: 2, offset: Offset(0, 1)),
];

ThemeData construireTheme() {
  final schema = ColorScheme.fromSeed(
    seedColor: Couleurs.emeraude,
    primary: Couleurs.emeraude,
    secondary: Couleurs.ambre,
    surface: Colors.white,
    error: Couleurs.rouge,
  );
  final base = ThemeData(colorScheme: schema, useMaterial3: true, fontFamily: policeMarque);
  final texte = base.textTheme.apply(
    bodyColor: Couleurs.texte,
    displayColor: Couleurs.texte,
    fontFamily: policeMarque,
  );
  final rondBouton = RoundedRectangleBorder(borderRadius: BorderRadius.circular(Mesures.rayonBouton));
  const styleBouton = TextStyle(fontFamily: policeMarque, fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: 0);

  return base.copyWith(
    scaffoldBackgroundColor: Couleurs.fond,
    splashFactory: InkSparkle.splashFactory,
    textTheme: texte.copyWith(
      headlineLarge: texte.headlineLarge?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.8),
      headlineMedium: texte.headlineMedium?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.6),
      headlineSmall: texte.headlineSmall?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.4),
      titleLarge: texte.titleLarge?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.3),
      titleMedium: texte.titleMedium?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.1),
      titleSmall: texte.titleSmall?.copyWith(fontWeight: FontWeight.w700),
      bodyLarge: texte.bodyLarge?.copyWith(height: 1.45),
      bodyMedium: texte.bodyMedium?.copyWith(height: 1.45),
      bodySmall: texte.bodySmall?.copyWith(color: Couleurs.texteDoux, height: 1.4, fontSize: 12.5),
      labelLarge: texte.labelLarge?.copyWith(fontWeight: FontWeight.w700),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Couleurs.fond,
      foregroundColor: Couleurs.texte,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      shadowColor: Couleurs.bordure,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: policeMarque,
        fontSize: 19,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.3,
        color: Couleurs.texte,
      ),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Mesures.rayonCarte),
        side: const BorderSide(color: Couleurs.bordure),
      ),
    ),
    listTileTheme: const ListTileThemeData(
      iconColor: Couleurs.emeraude,
      titleTextStyle: TextStyle(fontFamily: policeMarque, fontSize: 15, fontWeight: FontWeight.w600, color: Couleurs.texte),
      subtitleTextStyle: TextStyle(fontFamily: policeMarque, fontSize: 13, color: Couleurs.texteDoux, height: 1.35),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      hintStyle: const TextStyle(color: Color(0xFF94A3B8), fontWeight: FontWeight.w500),
      labelStyle: const TextStyle(color: Couleurs.texteDoux, fontWeight: FontWeight.w600),
      floatingLabelStyle: const TextStyle(color: Couleurs.emeraude, fontWeight: FontWeight.w700),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Mesures.rayonChamp),
        borderSide: const BorderSide(color: Couleurs.bordure),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Mesures.rayonChamp),
        borderSide: const BorderSide(color: Couleurs.bordure),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Mesures.rayonChamp),
        borderSide: const BorderSide(color: Couleurs.emeraude, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Mesures.rayonChamp),
        borderSide: const BorderSide(color: Couleurs.rouge),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      backgroundColor: Colors.white,
      selectedColor: Couleurs.menthe,
      side: WidgetStateBorderSide.resolveWith((etats) => BorderSide(
            color: etats.contains(WidgetState.selected) ? Couleurs.emeraude : Couleurs.bordure,
            width: etats.contains(WidgetState.selected) ? 1.4 : 1,
          )),
      shape: const StadiumBorder(),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      labelStyle: const TextStyle(fontFamily: policeMarque, fontWeight: FontWeight.w600, color: Couleurs.texte),
      checkmarkColor: Couleurs.emeraudeFonce,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 50),
        padding: const EdgeInsets.symmetric(horizontal: 20),
        shape: rondBouton,
        textStyle: styleBouton,
        elevation: 0,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(minimumSize: const Size(0, 50), shape: rondBouton, textStyle: styleBouton),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 50),
        padding: const EdgeInsets.symmetric(horizontal: 18),
        foregroundColor: Couleurs.emeraudeFonce,
        side: const BorderSide(color: Couleurs.bordure, width: 1.4),
        shape: rondBouton,
        textStyle: styleBouton,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: Couleurs.emeraude,
        shape: rondBouton,
        textStyle: styleBouton.copyWith(fontSize: 14),
      ),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: ButtonStyle(
        shape: WidgetStatePropertyAll(rondBouton),
        side: const WidgetStatePropertyAll(BorderSide(color: Couleurs.bordure)),
        textStyle: const WidgetStatePropertyAll(
            TextStyle(fontFamily: policeMarque, fontWeight: FontWeight.w700, fontSize: 13.5)),
        backgroundColor: WidgetStateProperty.resolveWith(
            (etats) => etats.contains(WidgetState.selected) ? Couleurs.menthe : Colors.white),
        foregroundColor: WidgetStateProperty.resolveWith(
            (etats) => etats.contains(WidgetState.selected) ? Couleurs.emeraudeFonce : Couleurs.texteDoux),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: Couleurs.emeraude,
      foregroundColor: Colors.white,
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      extendedTextStyle: styleBouton,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Couleurs.emeraudeFonce,
      contentTextStyle: const TextStyle(fontFamily: policeMarque, color: Colors.white, fontWeight: FontWeight.w600),
      actionTextColor: Couleurs.soleil,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      insetPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      titleTextStyle: const TextStyle(
          fontFamily: policeMarque, fontSize: 20, fontWeight: FontWeight.w800, color: Couleurs.texte, letterSpacing: -0.3),
      contentTextStyle: const TextStyle(fontFamily: policeMarque, fontSize: 15, color: Couleurs.texteDoux, height: 1.45),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      dragHandleColor: Color(0xFFCBD5E1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    ),
    tabBarTheme: const TabBarThemeData(
      labelStyle: TextStyle(fontFamily: policeMarque, fontWeight: FontWeight.w800, fontSize: 14.5),
      unselectedLabelStyle: TextStyle(fontFamily: policeMarque, fontWeight: FontWeight.w600, fontSize: 14.5),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Couleurs.emeraude,
      linearTrackColor: Couleurs.menthe,
      circularTrackColor: Couleurs.menthe,
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
          (etats) => etats.contains(WidgetState.selected) ? Colors.white : null),
      trackColor: WidgetStateProperty.resolveWith(
          (etats) => etats.contains(WidgetState.selected) ? Couleurs.emeraude : null),
    ),
    badgeTheme: const BadgeThemeData(backgroundColor: Couleurs.rouge, textColor: Colors.white),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(color: Couleurs.texte, borderRadius: BorderRadius.circular(8)),
      textStyle: const TextStyle(fontFamily: policeMarque, color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      indicatorColor: Couleurs.menthe,
      indicatorShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      elevation: 0,
      height: 70,
      iconTheme: WidgetStateProperty.resolveWith((etats) => IconThemeData(
            size: 24,
            color: etats.contains(WidgetState.selected) ? Couleurs.emeraudeFonce : Couleurs.texteDoux,
          )),
      labelTextStyle: WidgetStateProperty.resolveWith((etats) => TextStyle(
            fontFamily: policeMarque,
            fontSize: 12.5,
            fontWeight: etats.contains(WidgetState.selected) ? FontWeight.w800 : FontWeight.w600,
            color: etats.contains(WidgetState.selected) ? Couleurs.emeraudeFonce : Couleurs.texteDoux,
          )),
    ),
    dividerTheme: const DividerThemeData(color: Couleurs.bordure, space: 1, thickness: 1),
  );
}
