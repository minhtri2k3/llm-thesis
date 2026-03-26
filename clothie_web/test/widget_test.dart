import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:clothie_web/main.dart';

void main() {
  testWidgets('ClothieApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ClothieApp());
    // App should render without exceptions
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
