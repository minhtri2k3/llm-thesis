import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:clothie_web/providers/theme_provider.dart';
import 'package:clothie_web/theme/app_theme.dart';
import 'package:clothie_web/router/app_router.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
      ],
      child: const ClothieApp(),
    ),
  );
}

class ClothieApp extends StatelessWidget {
  const ClothieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return MaterialApp.router(
          title: 'Clothie — AI Fashion Assistant',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.lightTheme,
          darkTheme: AppTheme.darkTheme,
          themeMode: themeProvider.themeMode,
          routerConfig: appRouter,
        );
      },
    );
  }
}
