class QuestTemplate {
  final String id;
  final String familyId;
  final String name;
  final String? description;
  final String category;
  final int rewardMinutes;
  final String proofType;
  final bool aiVerify;
  final String recurrence;
  final bool active;
  final DateTime createdAt;

  QuestTemplate({
    required this.id,
    required this.familyId,
    required this.name,
    this.description,
    required this.category,
    required this.rewardMinutes,
    required this.proofType,
    required this.aiVerify,
    required this.recurrence,
    required this.active,
    required this.createdAt,
  });

  factory QuestTemplate.fromJson(Map<String, dynamic> json) {
    return QuestTemplate(
      id: json['id'],
      familyId: json['family_id'],
      name: json['name'],
      description: json['description'],
      category: json['category'],
      rewardMinutes: json['reward_minutes'],
      proofType: json['proof_type'],
      aiVerify: json['ai_verify'] ?? false,
      recurrence: json['recurrence'],
      active: json['active'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class QuestInstance {
  final String id;
  final String templateId;
  final String childId;
  final String status;
  final DateTime? claimedAt;
  final String? proofUrl;
  final Map<String, dynamic>? aiResult;
  final String? reviewedBy;
  final DateTime? reviewedAt;
  final String? generatedTanId;
  final DateTime createdAt;

  // Populated from template join
  String? templateName;
  String? templateCategory;
  int? rewardMinutes;
  String? proofType;

  QuestInstance({
    required this.id,
    required this.templateId,
    required this.childId,
    required this.status,
    this.claimedAt,
    this.proofUrl,
    this.aiResult,
    this.reviewedBy,
    this.reviewedAt,
    this.generatedTanId,
    required this.createdAt,
    this.templateName,
    this.templateCategory,
    this.rewardMinutes,
    this.proofType,
  });

  factory QuestInstance.fromJson(Map<String, dynamic> json) {
    return QuestInstance(
      id: json['id'],
      templateId: json['template_id'],
      childId: json['child_id'],
      status: json['status'],
      claimedAt: json['claimed_at'] != null ? DateTime.parse(json['claimed_at']) : null,
      proofUrl: json['proof_url'],
      aiResult: json['ai_result'],
      reviewedBy: json['reviewed_by'],
      reviewedAt: json['reviewed_at'] != null ? DateTime.parse(json['reviewed_at']) : null,
      generatedTanId: json['generated_tan_id'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
