import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:clothie_web/main.dart';
import 'package:clothie_web/providers/theme_provider.dart';
import 'package:clothie_web/config.dart';
import 'package:provider/provider.dart';

void main() {
  testWidgets('ClothieApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => ThemeProvider(),
        child: const ClothieApp(),
      ),
    );
    await tester.pump(Duration(seconds: kSplashDurationSeconds + 2));
    // App should render without exceptions
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
