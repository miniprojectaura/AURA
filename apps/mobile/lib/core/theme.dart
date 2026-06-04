/// AURA Design System — Blue palette, glassmorphism, premium typography.
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // ── Blue Palette (primary design language) ──────────────────────
  static const primary = Color(0xFF2E86DE);        // Core blue
  static const primaryLight = Color(0xFF54A0FF);    // Light blue accent
  static const primaryDark = Color(0xFF1B4F72);     // Dark blue (headers/nav)
  static const primaryDeep = Color(0xFF0C2844);     // Deepest blue

  // Surface blues
  static const background = Color(0xFFE8F4FD);     // Very light blue bg
  static const surface = Color(0xFFFFFFFF);         // White cards
  static const surfaceLight = Color(0xFFF0F7FC);    // Subtle blue tint
  static const surfaceLighter = Color(0xFFD6EBFA);  // Light blue fill
  static const border = Color(0xFFB8D4E8);          // Soft blue border
  static const borderLight = Color(0xFFD0E8F7);     // Lighter border

  // Text
  static const textPrimary = Color(0xFF1B3A5C);     // Dark blue text
  static const textSecondary = Color(0xFF5A7FA0);   // Medium blue text
  static const textMuted = Color(0xFF8BACC4);       // Light muted text
  static const textOnPrimary = Color(0xFFFFFFFF);   // White on blue

  // Semantic
  static const success = Color(0xFF2ECC71);
  static const warning = Color(0xFFF39C12);
  static const error = Color(0xFFE74C3C);
  static const info = Color(0xFF3498DB);

  // Accent (secondary blue shade)
  static const accent = Color(0xFF0ABDE3);          // Cyan-blue
  static const accentLight = Color(0xFF48DBFB);

  // Gradients
  static const gradientPrimary = LinearGradient(
    colors: [Color(0xFF2E86DE), Color(0xFF0ABDE3)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const gradientSurface = LinearGradient(
    colors: [Color(0xFFE8F4FD), Color(0xFFD6EBFA)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const gradientCard = LinearGradient(
    colors: [Color(0xFFFFFFFF), Color(0xFFF0F7FC)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // Keep for backward compat with glass_card.dart
  static const gradientGold = LinearGradient(
    colors: [Color(0xFF2E86DE), Color(0xFF54A0FF), Color(0xFF2E86DE)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

class AppTheme {
  static ThemeData get darkTheme => lightTheme; // Redirect to light

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.background,
      primaryColor: AppColors.primary,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primary,
        secondary: AppColors.accent,
        surface: AppColors.surface,
        error: AppColors.error,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: AppColors.textPrimary,
        outline: AppColors.border,
      ),
      textTheme: GoogleFonts.outfitTextTheme(
        const TextTheme(
          displayLarge: TextStyle(color: AppColors.textPrimary, fontSize: 32, fontWeight: FontWeight.w700, letterSpacing: -0.5),
          displayMedium: TextStyle(color: AppColors.textPrimary, fontSize: 28, fontWeight: FontWeight.w600, letterSpacing: -0.3),
          titleLarge: TextStyle(color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w600),
          titleMedium: TextStyle(color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w500),
          titleSmall: TextStyle(color: AppColors.textSecondary, fontSize: 14, fontWeight: FontWeight.w500),
          bodyLarge: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w400, height: 1.5),
          bodyMedium: TextStyle(color: AppColors.textSecondary, fontSize: 14, fontWeight: FontWeight.w400, height: 1.5),
          bodySmall: TextStyle(color: AppColors.textMuted, fontSize: 12, fontWeight: FontWeight.w400),
          labelLarge: TextStyle(color: AppColors.textPrimary, fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.5),
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: GoogleFonts.outfit(
          color: AppColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppColors.border, width: 0.5),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: const TextStyle(color: AppColors.textMuted),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceLight,
        selectedColor: AppColors.primary.withValues(alpha: 0.15),
        labelStyle: GoogleFonts.outfit(color: AppColors.textPrimary, fontSize: 13),
        side: const BorderSide(color: AppColors.border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.primaryDark,
        contentTextStyle: GoogleFonts.outfit(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
