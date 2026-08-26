import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baken_shell/main.dart';

void main() {
  testWidgets('Baken OS Desktop Shell Smoke Test', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const BakenOSDesktopApp());
    expect(find.text('BAKEN OS'), findsWidgets);
  });
}
