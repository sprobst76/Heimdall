import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:heimdall_child/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    // Mock the FlutterSecureStorage platform channel
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (MethodCall methodCall) async {
        if (methodCall.method == 'read') return null;
        if (methodCall.method == 'write') return null;
        if (methodCall.method == 'delete') return null;
        return null;
      },
    );
  });

  testWidgets('App renders without errors', (WidgetTester tester) async {
    await tester.pumpWidget(const HeimdallChildApp());
    await tester.pump();

    // LoginScreen should render since no auth token exists
    expect(find.text('HEIMDALL'), findsOneWidget);
  });
}
