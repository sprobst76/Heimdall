import 'dart:math';
import 'api_service.dart';

/// Mock-Implementation von ApiService für den Demo-Modus.
/// Alle Daten werden In-Memory gehalten und sind interaktiv veränderbar.
class MockApiService extends ApiService {
  bool _loggedIn = false;
  final List<Map<String, dynamic>> _questTemplates;
  final List<Map<String, dynamic>> _questInstances;
  final List<Map<String, dynamic>> _tans;

  MockApiService()
      : _questTemplates = _buildTemplates(),
        _questInstances = _buildInstances(),
        _tans = _buildTans();

  // --- Auth ---

  @override
  Future<Map<String, dynamic>> login(String email, String password) async {
    await Future.delayed(const Duration(milliseconds: 500));
    _loggedIn = true;
    return {
      'access_token': 'demo-token-12345',
      'refresh_token': 'demo-refresh-12345',
      'user_id': 'demo-child-1',
      'child_id': 'demo-child-1',
      'family_id': 'demo-family-1',
      'name': 'Max Mustermann',
      'role': 'child',
    };
  }

  @override
  Future<void> logout() async {
    _loggedIn = false;
  }

  @override
  Future<bool> isLoggedIn() async => _loggedIn;

  // --- Quests ---

  @override
  Future<List<dynamic>> getQuests(String childId, {String? status}) async {
    await Future.delayed(const Duration(milliseconds: 300));
    if (status != null) {
      return _questInstances.where((q) => q['status'] == status).toList();
    }
    return List.from(_questInstances);
  }

  @override
  Future<Map<String, dynamic>> claimQuest(String childId, String instanceId) async {
    await Future.delayed(const Duration(milliseconds: 400));
    final quest = _questInstances.firstWhere((q) => q['id'] == instanceId);
    quest['status'] = 'claimed';
    quest['claimed_at'] = DateTime.now().toIso8601String();
    return Map.from(quest);
  }

  @override
  Future<Map<String, dynamic>> submitProof(
      String childId, String instanceId, String proofType, String proofUrl) async {
    await Future.delayed(const Duration(milliseconds: 600));
    final quest = _questInstances.firstWhere((q) => q['id'] == instanceId);
    quest['status'] = 'pending_review';
    quest['proof_url'] = proofUrl;

    // Auto-approve nach kurzer Verzögerung
    Future.delayed(const Duration(seconds: 3), () {
      quest['status'] = 'approved';
      quest['reviewed_by'] = 'demo-parent-1';
      quest['reviewed_at'] = DateTime.now().toIso8601String();
      // Generiere Belohnungs-TAN
      final rewardTan = _generateTan(
        minutes: quest['reward_minutes'] ?? 30,
        source: 'quest',
      );
      quest['generated_tan_id'] = rewardTan['id'];
      _tans.add(rewardTan);
    });

    return Map.from(quest);
  }

  @override
  Future<Map<String, dynamic>> getQuestStats(String childId) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final approved = _questInstances.where((q) => q['status'] == 'approved').length;
    final total = _questInstances.length;
    final minutesEarned = _questInstances
        .where((q) => q['status'] == 'approved')
        .fold<int>(0, (sum, q) => sum + ((q['reward_minutes'] as int?) ?? 0));

    return {
      'completed_today': approved,
      'total_today': total,
      'minutes_earned_today': minutesEarned,
      'current_streak': 5,
    };
  }

  @override
  Future<List<dynamic>> getQuestTemplates(String familyId) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return List.from(_questTemplates);
  }

  // --- File Upload ---

  @override
  Future<Map<String, dynamic>> uploadProof(String filePath) async {
    await Future.delayed(const Duration(seconds: 1));
    return {
      'url': 'https://demo.heimdall.de/uploads/proof-${DateTime.now().millisecondsSinceEpoch}.jpg',
      'filename': filePath.split('/').last,
    };
  }

  // --- TANs ---

  @override
  Future<List<dynamic>> getTans(String childId, {String? status}) async {
    await Future.delayed(const Duration(milliseconds: 300));
    if (status != null) {
      return _tans.where((t) => t['status'] == status).toList();
    }
    return List.from(_tans);
  }

  @override
  Future<Map<String, dynamic>> redeemTan(String childId, String code) async {
    await Future.delayed(const Duration(milliseconds: 500));
    final tan = _tans.firstWhere(
      (t) => t['code'] == code && t['status'] == 'active',
      orElse: () => throw Exception('TAN nicht gefunden oder bereits eingelöst'),
    );
    tan['status'] = 'redeemed';
    tan['redeemed_at'] = DateTime.now().toIso8601String();
    return Map.from(tan);
  }

  // --- Chat ---

  @override
  Future<String> chat(String message, List<Map<String, String>> history) async {
    await Future.delayed(const Duration(milliseconds: 800));
    final lower = message.toLowerCase();

    if (lower.contains('bildschirmzeit') || lower.contains('screen') || lower.contains('zeit')) {
      return 'Du hast heute noch 45 Minuten Bildschirmzeit übrig. '
          'Durch das Erledigen von Quests kannst du dir zusätzliche Zeit verdienen! 🎮';
    }
    if (lower.contains('quest') || lower.contains('aufgabe')) {
      return 'Du hast aktuell 3 verfügbare Quests: "Zimmer aufräumen", "Hund ausführen" und '
          '"Buch lesen". Schau mal im Quest-Tab nach! 📋';
    }
    if (lower.contains('tan') || lower.contains('code')) {
      return 'TANs sind Belohnungscodes, die du durch Quests verdienst oder von deinen Eltern '
          'bekommst. Du kannst sie im TAN-Tab einlösen, um Bildschirmzeit freizuschalten. 🔑';
    }
    if (lower.contains('regel') || lower.contains('regel')) {
      return 'Deine aktuellen Regeln: Schultage max. 2 Stunden, Wochenende max. 3 Stunden. '
          'Keine Bildschirmzeit nach 20:00 Uhr. 📏';
    }
    if (lower.contains('hallo') || lower.contains('hi') || lower.contains('hey')) {
      return 'Hallo Max! 👋 Wie kann ich dir helfen? Frag mich nach Bildschirmzeit, '
          'Quests, TANs oder Regeln.';
    }
    return 'Ich bin dein Heimdall-Assistent! Du kannst mich nach deiner Bildschirmzeit, '
        'verfügbaren Quests, TANs oder den aktuellen Regeln fragen. 🛡️';
  }

  // --- Hilfsfunktionen ---

  Map<String, dynamic> _generateTan({required int minutes, required String source}) {
    final words = ['ODIN', 'THOR', 'FREYA', 'LOKI', 'FENRIR', 'BALDUR', 'TYR', 'HELA'];
    final rng = Random();
    final code = '${words[rng.nextInt(words.length)]}-${rng.nextInt(9000) + 1000}';
    return {
      'id': 'tan-${DateTime.now().millisecondsSinceEpoch}',
      'child_id': 'demo-child-1',
      'code': code,
      'type': 'time',
      'value_minutes': minutes,
      'expires_at': DateTime.now().add(const Duration(days: 7)).toIso8601String(),
      'single_use': true,
      'source': source,
      'status': 'active',
      'created_at': DateTime.now().toIso8601String(),
    };
  }

  static List<Map<String, dynamic>> _buildTemplates() {
    final now = DateTime.now().toIso8601String();
    return [
      {
        'id': 'tpl-1',
        'family_id': 'demo-family-1',
        'name': 'Zimmer aufräumen',
        'description': 'Dein Zimmer ordentlich aufräumen und Staubsaugen.',
        'category': 'haushalt',
        'reward_minutes': 30,
        'proof_type': 'photo',
        'ai_verify': true,
        'recurrence': 'daily',
        'active': true,
        'created_at': now,
      },
      {
        'id': 'tpl-2',
        'family_id': 'demo-family-1',
        'name': 'Hausaufgaben erledigen',
        'description': 'Alle Hausaufgaben für morgen fertig machen.',
        'category': 'schule',
        'reward_minutes': 45,
        'proof_type': 'photo',
        'ai_verify': false,
        'recurrence': 'weekdays',
        'active': true,
        'created_at': now,
      },
      {
        'id': 'tpl-3',
        'family_id': 'demo-family-1',
        'name': 'Müll rausbringen',
        'description': 'Gelben Sack und Restmüll zur Tonne bringen.',
        'category': 'haushalt',
        'reward_minutes': 15,
        'proof_type': 'text',
        'ai_verify': false,
        'recurrence': 'weekly',
        'active': true,
        'created_at': now,
      },
      {
        'id': 'tpl-4',
        'family_id': 'demo-family-1',
        'name': 'Hund ausführen',
        'description': 'Mindestens 20 Minuten mit dem Hund Gassi gehen.',
        'category': 'freizeit',
        'reward_minutes': 20,
        'proof_type': 'photo',
        'ai_verify': true,
        'recurrence': 'daily',
        'active': true,
        'created_at': now,
      },
      {
        'id': 'tpl-5',
        'family_id': 'demo-family-1',
        'name': 'Buch lesen',
        'description': 'Mindestens 30 Minuten in einem Buch lesen.',
        'category': 'bildung',
        'reward_minutes': 30,
        'proof_type': 'text',
        'ai_verify': false,
        'recurrence': 'daily',
        'active': true,
        'created_at': now,
      },
    ];
  }

  static List<Map<String, dynamic>> _buildInstances() {
    final now = DateTime.now();
    return [
      {
        'id': 'qi-1',
        'template_id': 'tpl-1',
        'child_id': 'demo-child-1',
        'status': 'available',
        'claimed_at': null,
        'proof_url': null,
        'ai_result': null,
        'reviewed_by': null,
        'reviewed_at': null,
        'generated_tan_id': null,
        'created_at': now.toIso8601String(),
        'template_name': 'Zimmer aufräumen',
        'template_category': 'haushalt',
        'reward_minutes': 30,
        'proof_type': 'photo',
      },
      {
        'id': 'qi-2',
        'template_id': 'tpl-2',
        'child_id': 'demo-child-1',
        'status': 'claimed',
        'claimed_at': now.subtract(const Duration(hours: 1)).toIso8601String(),
        'proof_url': null,
        'ai_result': null,
        'reviewed_by': null,
        'reviewed_at': null,
        'generated_tan_id': null,
        'created_at': now.toIso8601String(),
        'template_name': 'Hausaufgaben erledigen',
        'template_category': 'schule',
        'reward_minutes': 45,
        'proof_type': 'photo',
      },
      {
        'id': 'qi-3',
        'template_id': 'tpl-3',
        'child_id': 'demo-child-1',
        'status': 'approved',
        'claimed_at': now.subtract(const Duration(hours: 3)).toIso8601String(),
        'proof_url': 'https://demo.heimdall.de/uploads/proof-muell.jpg',
        'ai_result': null,
        'reviewed_by': 'demo-parent-1',
        'reviewed_at': now.subtract(const Duration(hours: 2)).toIso8601String(),
        'generated_tan_id': 'tan-reward-1',
        'created_at': now.toIso8601String(),
        'template_name': 'Müll rausbringen',
        'template_category': 'haushalt',
        'reward_minutes': 15,
        'proof_type': 'text',
      },
      {
        'id': 'qi-4',
        'template_id': 'tpl-4',
        'child_id': 'demo-child-1',
        'status': 'available',
        'claimed_at': null,
        'proof_url': null,
        'ai_result': null,
        'reviewed_by': null,
        'reviewed_at': null,
        'generated_tan_id': null,
        'created_at': now.toIso8601String(),
        'template_name': 'Hund ausführen',
        'template_category': 'freizeit',
        'reward_minutes': 20,
        'proof_type': 'photo',
      },
      {
        'id': 'qi-5',
        'template_id': 'tpl-5',
        'child_id': 'demo-child-1',
        'status': 'available',
        'claimed_at': null,
        'proof_url': null,
        'ai_result': null,
        'reviewed_by': null,
        'reviewed_at': null,
        'generated_tan_id': null,
        'created_at': now.toIso8601String(),
        'template_name': 'Buch lesen',
        'template_category': 'bildung',
        'reward_minutes': 30,
        'proof_type': 'text',
      },
    ];
  }

  static List<Map<String, dynamic>> _buildTans() {
    final now = DateTime.now();
    final expires = now.add(const Duration(days: 7)).toIso8601String();
    return [
      {
        'id': 'tan-1',
        'child_id': 'demo-child-1',
        'code': 'ODIN-3382',
        'type': 'time',
        'value_minutes': 30,
        'expires_at': expires,
        'single_use': true,
        'source': 'parent',
        'status': 'active',
        'created_at': now.subtract(const Duration(days: 1)).toIso8601String(),
      },
      {
        'id': 'tan-2',
        'child_id': 'demo-child-1',
        'code': 'THOR-1547',
        'type': 'time',
        'value_minutes': 45,
        'expires_at': expires,
        'single_use': true,
        'source': 'quest',
        'status': 'active',
        'created_at': now.subtract(const Duration(days: 2)).toIso8601String(),
      },
      {
        'id': 'tan-3',
        'child_id': 'demo-child-1',
        'code': 'FREYA-8821',
        'type': 'time',
        'value_minutes': 60,
        'expires_at': expires,
        'single_use': true,
        'source': 'parent',
        'status': 'active',
        'created_at': now.subtract(const Duration(hours: 12)).toIso8601String(),
      },
      {
        'id': 'tan-4',
        'child_id': 'demo-child-1',
        'code': 'LOKI-4456',
        'type': 'time',
        'value_minutes': 15,
        'expires_at': expires,
        'single_use': true,
        'source': 'quest',
        'status': 'active',
        'created_at': now.subtract(const Duration(hours: 6)).toIso8601String(),
      },
      {
        'id': 'tan-5',
        'child_id': 'demo-child-1',
        'code': 'HERO-7749',
        'type': 'time',
        'value_minutes': 30,
        'expires_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'single_use': true,
        'source': 'parent',
        'status': 'redeemed',
        'redeemed_at': now.subtract(const Duration(days: 2)).toIso8601String(),
        'created_at': now.subtract(const Duration(days: 5)).toIso8601String(),
      },
      {
        'id': 'tan-6',
        'child_id': 'demo-child-1',
        'code': 'FENRIR-2103',
        'type': 'time',
        'value_minutes': 20,
        'expires_at': now.subtract(const Duration(hours: 12)).toIso8601String(),
        'single_use': true,
        'source': 'quest',
        'status': 'redeemed',
        'redeemed_at': now.subtract(const Duration(days: 1)).toIso8601String(),
        'created_at': now.subtract(const Duration(days: 3)).toIso8601String(),
      },
    ];
  }
}
