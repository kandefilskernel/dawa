import 'package:flutter/material.dart';

/// Palette de la marque Dawa.
abstract final class Couleurs {
  static const emeraude = Color(0xFF0B8F6A);
  static const emeraudeFonce = Color(0xFF064E3B);
  static const menthe = Color(0xFFD1FAE5);
  static const ambre = Color(0xFFF59E0B);
  static const ambreClair = Color(0xFFFEF3C7);
  /// Ambre assez foncé pour porter du texte blanc ou être lu sur fond clair.
  static const ambreFonce = Color(0xFFB45309);
  static const indigo = Color(0xFF4338CA);
  static const indigoFonce = Color(0xFF1E1B4B);
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
}

const ombreDouce = [
  BoxShadow(color: Color(0x14000000), blurRadius: 24, offset: Offset(0, 8)),
];

ThemeData construireTheme() {
  final schema = ColorScheme.fromSeed(
    seedColor: Couleurs.emeraude,
    primary: Couleurs.emeraude,
    secondary: Couleurs.ambre,
    surface: Colors.white,
  );
  final base = ThemeData(colorScheme: schema, useMaterial3: true);
  final texte = base.textTheme.apply(bodyColor: Couleurs.texte, displayColor: Couleurs.texte);

  return base.copyWith(
    scaffoldBackgroundColor: Couleurs.fond,
    textTheme: texte.copyWith(
      headlineMedium: texte.headlineMedium?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5),
      titleLarge: texte.titleLarge?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.2),
      titleMedium: texte.titleMedium?.copyWith(fontWeight: FontWeight.w700),
      bodySmall: texte.bodySmall?.copyWith(color: Couleurs.texteDoux),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Couleurs.fond,
      foregroundColor: Couleurs.texte,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Couleurs.texte),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: Couleurs.bordure),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      hintStyle: const TextStyle(color: Couleurs.texteDoux),
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: Couleurs.emeraude, width: 2),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      backgroundColor: Colors.white,
      selectedColor: Couleurs.menthe,
      side: const BorderSide(color: Couleurs.bordure),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      labelStyle: const TextStyle(fontWeight: FontWeight.w600, color: Couleurs.texte),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 48),
        side: const BorderSide(color: Couleurs.bordure),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      indicatorColor: Couleurs.menthe,
      elevation: 0,
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith((etats) => TextStyle(
            fontSize: 13,
            fontWeight: etats.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
            color: etats.contains(WidgetState.selected) ? Couleurs.emeraudeFonce : Couleurs.texteDoux,
          )),
    ),
    dividerTheme: const DividerThemeData(color: Couleurs.bordure, space: 1),
  );
}
