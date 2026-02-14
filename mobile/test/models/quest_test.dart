import 'package:flutter_test/flutter_test.dart';
import 'package:heimdall_child/models/quest.dart';

void main() {
  group('QuestTemplate', () {
    test('fromJson parses all fields', () {
      final json = {
        'id': 'tmpl-1',
        'family_id': 'fam-1',
        'name': 'Zimmer aufräumen',
        'description': 'Das Kinderzimmer ordentlich machen',
        'category': 'Haushalt',
        'reward_minutes': 30,
        'proof_type': 'photo',
        'ai_verify': true,
        'recurrence': 'daily',
        'active': true,
        'created_at': '2025-01-15T10:00:00Z',
      };

      final template = QuestTemplate.fromJson(json);

      expect(template.id, 'tmpl-1');
      expect(template.familyId, 'fam-1');
      expect(template.name, 'Zimmer aufräumen');
      expect(template.description, 'Das Kinderzimmer ordentlich machen');
      expect(template.category, 'Haushalt');
      expect(template.rewardMinutes, 30);
      expect(template.proofType, 'photo');
      expect(template.aiVerify, true);
      expect(template.recurrence, 'daily');
      expect(template.active, true);
    });

    test('fromJson handles null optionals', () {
      final json = {
        'id': 'tmpl-2',
        'family_id': 'fam-1',
        'name': 'Lesen',
        'description': null,
        'category': 'Schule',
        'reward_minutes': 15,
        'proof_type': 'text',
        'recurrence': 'daily',
        'created_at': '2025-01-15T10:00:00Z',
      };

      final template = QuestTemplate.fromJson(json);

      expect(template.description, isNull);
      expect(template.aiVerify, false); // default
      expect(template.active, true); // default
    });
  });

  group('QuestInstance', () {
    test('fromJson parses all fields', () {
      final json = {
        'id': 'inst-1',
        'template_id': 'tmpl-1',
        'child_id': 'child-1',
        'status': 'approved',
        'claimed_at': '2025-01-15T11:00:00Z',
        'proof_url': '/uploads/proof/img.jpg',
        'ai_result': {'approved': true, 'confidence': 85},
        'reviewed_by': 'parent-1',
        'reviewed_at': '2025-01-15T12:00:00Z',
        'generated_tan_id': 'tan-1',
        'created_at': '2025-01-15T10:00:00Z',
      };

      final instance = QuestInstance.fromJson(json);

      expect(instance.id, 'inst-1');
      expect(instance.templateId, 'tmpl-1');
      expect(instance.childId, 'child-1');
      expect(instance.status, 'approved');
      expect(instance.claimedAt, isNotNull);
      expect(instance.proofUrl, '/uploads/proof/img.jpg');
      expect(instance.aiResult, isNotNull);
      expect(instance.aiResult!['confidence'], 85);
      expect(instance.reviewedBy, 'parent-1');
      expect(instance.reviewedAt, isNotNull);
      expect(instance.generatedTanId, 'tan-1');
    });

    test('fromJson handles null optional fields', () {
      final json = {
        'id': 'inst-2',
        'template_id': 'tmpl-1',
        'child_id': 'child-1',
        'status': 'available',
        'created_at': '2025-01-15T10:00:00Z',
      };

      final instance = QuestInstance.fromJson(json);

      expect(instance.status, 'available');
      expect(instance.claimedAt, isNull);
      expect(instance.proofUrl, isNull);
      expect(instance.aiResult, isNull);
      expect(instance.reviewedBy, isNull);
      expect(instance.reviewedAt, isNull);
      expect(instance.generatedTanId, isNull);
    });

    test('mutable template fields can be set', () {
      final instance = QuestInstance.fromJson({
        'id': 'inst-3',
        'template_id': 'tmpl-1',
        'child_id': 'child-1',
        'status': 'available',
        'created_at': '2025-01-15T10:00:00Z',
      });

      expect(instance.templateName, isNull);

      instance.templateName = 'Zimmer aufräumen';
      instance.templateCategory = 'Haushalt';
      instance.rewardMinutes = 30;
      instance.proofType = 'photo';

      expect(instance.templateName, 'Zimmer aufräumen');
      expect(instance.templateCategory, 'Haushalt');
      expect(instance.rewardMinutes, 30);
      expect(instance.proofType, 'photo');
    });
  });
}
