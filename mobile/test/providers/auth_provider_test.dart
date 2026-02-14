import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:heimdall_child/providers/auth_provider.dart';
import 'package:heimdall_child/services/api_service.dart';

class MockApiService extends Mock implements ApiService {}

void main() {
  late MockApiService mockApi;
  late AuthProvider provider;

  setUp(() {
    mockApi = MockApiService();
    provider = AuthProvider(mockApi);
  });

  group('AuthProvider', () {
    test('initial state is logged out', () {
      expect(provider.isLoggedIn, false);
      expect(provider.childId, isNull);
      expect(provider.familyId, isNull);
      expect(provider.childName, isNull);
    });

    test('checkAuth sets isLoggedIn true when token exists', () async {
      when(() => mockApi.isLoggedIn()).thenAnswer((_) async => true);

      await provider.checkAuth();

      expect(provider.isLoggedIn, true);
    });

    test('checkAuth sets isLoggedIn false when no token', () async {
      when(() => mockApi.isLoggedIn()).thenAnswer((_) async => false);

      await provider.checkAuth();

      expect(provider.isLoggedIn, false);
    });

    test('login success sets isLoggedIn true', () async {
      when(() => mockApi.login('test@test.de', 'password123'))
          .thenAnswer((_) async => {'access_token': 'tok', 'refresh_token': 'ref'});

      final result = await provider.login('test@test.de', 'password123');

      expect(result, true);
      expect(provider.isLoggedIn, true);
    });

    test('login failure returns false', () async {
      when(() => mockApi.login('test@test.de', 'wrong'))
          .thenThrow(Exception('401'));

      final result = await provider.login('test@test.de', 'wrong');

      expect(result, false);
      expect(provider.isLoggedIn, false);
    });

    test('setChildInfo stores child data', () {
      provider.setChildInfo('child-1', 'fam-1', 'Leo');

      expect(provider.childId, 'child-1');
      expect(provider.familyId, 'fam-1');
      expect(provider.childName, 'Leo');
    });

    test('logout clears all state', () async {
      when(() => mockApi.logout()).thenAnswer((_) async {});
      when(() => mockApi.login('x@x.de', 'p'))
          .thenAnswer((_) async => {'access_token': 'a', 'refresh_token': 'r'});

      await provider.login('x@x.de', 'p');
      provider.setChildInfo('c1', 'f1', 'Leo');
      expect(provider.isLoggedIn, true);

      await provider.logout();

      expect(provider.isLoggedIn, false);
      expect(provider.childId, isNull);
      expect(provider.familyId, isNull);
      expect(provider.childName, isNull);
    });

    test('notifies listeners on state change', () async {
      when(() => mockApi.isLoggedIn()).thenAnswer((_) async => true);

      var notified = false;
      provider.addListener(() => notified = true);

      await provider.checkAuth();
      expect(notified, true);
    });
  });
}
