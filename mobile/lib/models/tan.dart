class Tan {
  final String id;
  final String childId;
  final String code;
  final String type;
  final List<String>? scopeGroups;
  final int? valueMinutes;
  final String? valueUnlockUntil;
  final DateTime expiresAt;
  final bool singleUse;
  final String? source;
  final String status;
  final DateTime? redeemedAt;
  final DateTime createdAt;

  Tan({
    required this.id,
    required this.childId,
    required this.code,
    required this.type,
    this.scopeGroups,
    this.valueMinutes,
    this.valueUnlockUntil,
    required this.expiresAt,
    required this.singleUse,
    this.source,
    required this.status,
    this.redeemedAt,
    required this.createdAt,
  });

  factory Tan.fromJson(Map<String, dynamic> json) {
    return Tan(
      id: json['id'],
      childId: json['child_id'],
      code: json['code'],
      type: json['type'],
      scopeGroups: json['scope_groups'] != null
          ? List<String>.from(json['scope_groups'])
          : null,
      valueMinutes: json['value_minutes'],
      valueUnlockUntil: json['value_unlock_until'],
      expiresAt: DateTime.parse(json['expires_at']),
      singleUse: json['single_use'] ?? true,
      source: json['source'],
      status: json['status'],
      redeemedAt: json['redeemed_at'] != null ? DateTime.parse(json['redeemed_at']) : null,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
