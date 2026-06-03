// Basic smoke test for the Fashion AI app.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:fashion_ai/main.dart';

void main() {
  testWidgets('FashionAIApp renders without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: FashionAIApp()),
    );
    // Verify that the app builds and renders something
    expect(find.byType(FashionAIApp), findsOneWidget);
  });
}
