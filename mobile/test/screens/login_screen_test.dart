import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:heimdall_child/providers/auth_provider.dart';
import 'package:heimdall_child/screens/login_screen.dart';
import 'package:heimdall_child/services/api_service.dart';

class MockApiService extends Mock implements ApiService {}

void main() {
  late MockApiService mockApi;

  setUp(() {
    mockApi = MockApiService();
  });

  Widget createApp() {
    return MaterialApp(
      home: ChangeNotifierProvider(
        create: (_) => AuthProvider(mockApi),
        child: const LoginScreen(),
      ),
    );
  }

  group('LoginScreen', () {
    testWidgets('renders email and password fields', (tester) async {
      await tester.pumpWidget(createApp());

      expect(find.text('E-Mail'), findsOneWidget);
      expect(find.text('Passwort'), findsOneWidget);
      expect(find.text('Anmelden'), findsOneWidget);
      expect(find.text('HEIMDALL'), findsOneWidget);
    });

    testWidgets('shows validation error on empty submit', (tester) async {
      await tester.pumpWidget(createApp());

      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      expect(find.text('Bitte E-Mail eingeben'), findsOneWidget);
      expect(find.text('Bitte Passwort eingeben'), findsOneWidget);
    });

    testWidgets('shows error message on failed login', (tester) async {
      when(() => mockApi.login('test@test.de', 'wrong'))
          .thenThrow(Exception('401'));

      await tester.pumpWidget(createApp());

      await tester.enterText(
        find.widgetWithText(TextFormField, 'E-Mail'),
        'test@test.de',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Passwort'),
        'wrong',
      );
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      expect(
        find.text('Anmeldung fehlgeschlagen. Bitte prüfe deine Zugangsdaten.'),
        findsOneWidget,
      );
    });

    testWidgets('does not show error initially', (tester) async {
      await tester.pumpWidget(createApp());

      expect(
        find.text('Anmeldung fehlgeschlagen. Bitte prüfe deine Zugangsdaten.'),
        findsNothing,
      );
    });
  });
}
