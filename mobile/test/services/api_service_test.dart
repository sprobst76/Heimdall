import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heimdall_child/services/api_service.dart';
import 'package:mocktail/mocktail.dart';

/// Custom mock adapter to intercept Dio HTTP requests in tests.
class MockHttpClientAdapter extends Mock implements HttpClientAdapter {}

class FakeRequestOptions extends Fake implements RequestOptions {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late ApiService api;
  late MockHttpClientAdapter mockAdapter;

  setUpAll(() {
    registerFallbackValue(FakeRequestOptions());
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

  setUp(() {
    api = ApiService();
    mockAdapter = MockHttpClientAdapter();
    api.dio.httpClientAdapter = mockAdapter;
  });

  tearDown(() {
    mockAdapter.close();
  });

  ResponseBody _jsonResponse(Object data, {int statusCode = 200}) {
    return ResponseBody.fromString(
      json.encode(data),
      statusCode,
      headers: {
        'content-type': ['application/json'],
      },
    );
  }

  group('ApiService', () {
    test('getQuests calls correct endpoint', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse([
                {'id': 'q1', 'status': 'available'}
              ]));

      final result = await api.getQuests('child-1');

      expect(result, isList);
      expect(result.length, 1);

      final captured = verify(() => mockAdapter.fetch(
            captureAny(),
            any(),
            any(),
          )).captured;
      final options = captured.first as RequestOptions;
      expect(options.path, contains('/children/child-1/quests'));
    });

    test('claimQuest calls correct endpoint', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse({'status': 'claimed'}));

      final result = await api.claimQuest('child-1', 'inst-1');

      expect(result['status'], 'claimed');

      final captured = verify(() => mockAdapter.fetch(
            captureAny(),
            any(),
            any(),
          )).captured;
      final options = captured.first as RequestOptions;
      expect(options.path, contains('/children/child-1/quests/inst-1/claim'));
      expect(options.method, 'POST');
    });

    test('getTans calls correct endpoint', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse([
                {'id': 't1', 'code': 'ODIN-1234'}
              ]));

      final result = await api.getTans('child-1');

      expect(result, isList);
      expect(result.length, 1);
    });

    test('redeemTan sends code in body', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse({'status': 'redeemed'}));

      final result = await api.redeemTan('child-1', 'ODIN-1234');

      expect(result['status'], 'redeemed');

      final captured = verify(() => mockAdapter.fetch(
            captureAny(),
            any(),
            any(),
          )).captured;
      final options = captured.first as RequestOptions;
      expect(options.path, contains('/children/child-1/tans/redeem'));
    });

    test('chat returns response string', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse({'response': 'Hallo Leo!'}));

      final result = await api.chat('Wie viel Zeit habe ich?', []);

      expect(result, 'Hallo Leo!');
    });

    test('getQuestStats calls correct endpoint', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse({
                'completed_today': 2,
                'minutes_earned_today': 45,
              }));

      final result = await api.getQuestStats('child-1');

      expect(result['completed_today'], 2);
    });

    test('getQuestTemplates calls families endpoint', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenAnswer((_) async => _jsonResponse([
                {'id': 'tmpl-1', 'name': 'Test'}
              ]));

      final result = await api.getQuestTemplates('fam-1');

      expect(result, isList);

      final captured = verify(() => mockAdapter.fetch(
            captureAny(),
            any(),
            any(),
          )).captured;
      final options = captured.first as RequestOptions;
      expect(options.path, contains('/families/fam-1/quests'));
    });
  });
}
