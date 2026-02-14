import 'package:flutter_test/flutter_test.dart';
import 'package:heimdall_child/models/tan.dart';

void main() {
  group('Tan', () {
    test('fromJson parses all fields', () {
      final json = {
        'id': 'tan-1',
        'child_id': 'child-1',
        'code': 'ODIN-3382',
        'type': 'time',
        'scope_groups': ['browser-group', 'games-group'],
        'value_minutes': 60,
        'value_unlock_until': null,
        'expires_at': '2025-01-20T23:59:59Z',
        'single_use': true,
        'source': 'quest',
        'status': 'unused',
        'redeemed_at': null,
        'created_at': '2025-01-15T10:00:00Z',
      };

      final tan = Tan.fromJson(json);

      expect(tan.id, 'tan-1');
      expect(tan.childId, 'child-1');
      expect(tan.code, 'ODIN-3382');
      expect(tan.type, 'time');
      expect(tan.scopeGroups, ['browser-group', 'games-group']);
      expect(tan.valueMinutes, 60);
      expect(tan.valueUnlockUntil, isNull);
      expect(tan.singleUse, true);
      expect(tan.source, 'quest');
      expect(tan.status, 'unused');
      expect(tan.redeemedAt, isNull);
    });

    test('fromJson handles minimal fields', () {
      final json = {
        'id': 'tan-2',
        'child_id': 'child-1',
        'code': 'HERO-7749',
        'type': 'unlock',
        'expires_at': '2025-01-20T23:59:59Z',
        'status': 'redeemed',
        'redeemed_at': '2025-01-16T14:30:00Z',
        'created_at': '2025-01-15T10:00:00Z',
      };

      final tan = Tan.fromJson(json);

      expect(tan.code, 'HERO-7749');
      expect(tan.type, 'unlock');
      expect(tan.scopeGroups, isNull);
      expect(tan.valueMinutes, isNull);
      expect(tan.source, isNull);
      expect(tan.singleUse, true); // default
      expect(tan.status, 'redeemed');
      expect(tan.redeemedAt, isNotNull);
    });

    test('fromJson parses dates correctly', () {
      final json = {
        'id': 'tan-3',
        'child_id': 'child-1',
        'code': 'THOR-1234',
        'type': 'time',
        'expires_at': '2025-06-15T18:00:00Z',
        'status': 'unused',
        'created_at': '2025-06-01T08:00:00Z',
      };

      final tan = Tan.fromJson(json);

      expect(tan.expiresAt.year, 2025);
      expect(tan.expiresAt.month, 6);
      expect(tan.createdAt.day, 1);
    });
  });
}
