import 'package:flutter_test/flutter_test.dart';

import 'package:heimdall_child/main.dart';

void main() {
  testWidgets('App renders without errors', (WidgetTester tester) async {
    await tester.pumpWidget(const HeimdallChildApp());
    await tester.pumpAndSettle();

    expect(find.text('Heimdall'), findsOneWidget);
  });
}
