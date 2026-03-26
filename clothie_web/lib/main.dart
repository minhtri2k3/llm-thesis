import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:clothie_web/config.dart';
import 'package:clothie_web/screens/splash_screen.dart';

void main() {
  runApp(const ClothieApp());
}

class ClothieApp extends StatelessWidget {
  const ClothieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Clothie — AI Fashion Assistant',
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(),
      home: const SplashScreen(),
    );
  }

  ThemeData _buildTheme() {
    final base = ThemeData.dark();
    return base.copyWith(
      scaffoldBackgroundColor: const Color(kBgColor),
      colorScheme: const ColorScheme.dark(
        primary: Color(kAccentColor),
        secondary: Color(kAccentLight),
        surface: Color(kSurfaceColor),
        onSurface: Color(kTextPrimary),
      ),
      textTheme: GoogleFonts.outfitTextTheme(base.textTheme).apply(
        bodyColor: const Color(kTextPrimary),
        displayColor: const Color(kTextPrimary),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(kSurfaceColor),
        foregroundColor: Color(kTextPrimary),
        elevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(kCardColor),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.08)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: const Color(kAccentColor),
        contentTextStyle: GoogleFonts.outfit(color: Colors.white),
      ),
    );
  }
}
