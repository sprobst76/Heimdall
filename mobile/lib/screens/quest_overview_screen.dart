import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/quest.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import 'quest_detail_screen.dart';

class QuestOverviewScreen extends StatefulWidget {
  const QuestOverviewScreen({super.key});

  @override
  State<QuestOverviewScreen> createState() => _QuestOverviewScreenState();
}

class _QuestOverviewScreenState extends State<QuestOverviewScreen> {
  List<QuestInstance> _quests = [];
  Map<String, dynamic> _stats = {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final auth = context.read<AuthProvider>();
    final api = context.read<ApiService>();
    final childId = auth.childId;

    if (childId == null) {
      setState(() {
        _error = 'Kein Kind-Profil ausgewählt';
        _loading = false;
      });
      return;
    }

    try {
      final results = await Future.wait([
        api.getQuests(childId),
        api.getQuestStats(childId),
        auth.familyId != null
            ? api.getQuestTemplates(auth.familyId!)
            : Future.value(<dynamic>[]),
      ]);

      final questsJson = results[0] as List<dynamic>;
      final stats = results[1] as Map<String, dynamic>;
      final templatesJson = results[2] as List<dynamic>;

      final templates = <String, QuestTemplate>{};
      for (final t in templatesJson) {
        final template = QuestTemplate.fromJson(t as Map<String, dynamic>);
        templates[template.id] = template;
      }

      final quests = questsJson.map((q) {
        final instance = QuestInstance.fromJson(q as Map<String, dynamic>);
        final template = templates[instance.templateId];
        if (template != null) {
          instance.templateName = template.name;
          instance.templateCategory = template.category;
          instance.rewardMinutes = template.rewardMinutes;
          instance.proofType = template.proofType;
        }
        return instance;
      }).toList();

      if (mounted) {
        setState(() {
          _quests = quests;
          _stats = stats;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Fehler beim Laden: $e';
          _loading = false;
        });
      }
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'available':
        return Colors.blue;
      case 'claimed':
        return Colors.amber;
      case 'pending_review':
        return Colors.orange;
      case 'approved':
        return Colors.green;
      case 'rejected':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'available':
        return 'Verfügbar';
      case 'claimed':
        return 'Angenommen';
      case 'pending_review':
        return 'Wird geprüft';
      case 'approved':
        return 'Erledigt';
      case 'rejected':
        return 'Abgelehnt';
      default:
        return status;
    }
  }

  IconData _categoryIcon(String? category) {
    switch (category) {
      case 'Haushalt':
        return Icons.home;
      case 'Schule':
        return Icons.school;
      case 'Bonus':
        return Icons.star;
      default:
        return Icons.emoji_events;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
            const SizedBox(height: 16),
            Text(_error!, style: theme.textTheme.bodyLarge),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () {
                setState(() {
                  _loading = true;
                  _error = null;
                });
                _loadData();
              },
              child: const Text('Erneut versuchen'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Stats card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _StatItem(
                    icon: Icons.check_circle,
                    value: '${_stats['completed_today'] ?? 0}/${_stats['total_today'] ?? 0}',
                    label: 'Heute erledigt',
                    color: Colors.green,
                  ),
                  _StatItem(
                    icon: Icons.timer,
                    value: '${_stats['minutes_earned_today'] ?? 0} Min',
                    label: 'Verdient',
                    color: theme.colorScheme.primary,
                  ),
                  _StatItem(
                    icon: Icons.local_fire_department,
                    value: '${_stats['current_streak'] ?? 0}',
                    label: 'Streak',
                    color: Colors.orange,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Active quests
          Text(
            'Aktive Quests',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),

          ..._quests
              .where((q) => q.status == 'available' || q.status == 'claimed')
              .map((quest) => _QuestCard(
                    quest: quest,
                    statusColor: _statusColor(quest.status),
                    statusLabel: _statusLabel(quest.status),
                    categoryIcon: _categoryIcon(quest.templateCategory),
                    onTap: () => _openQuestDetail(quest),
                  )),

          if (_quests.where((q) => q.status == 'available' || q.status == 'claimed').isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Icon(Icons.emoji_events_outlined,
                        size: 48, color: theme.colorScheme.onSurfaceVariant),
                    const SizedBox(height: 8),
                    Text(
                      'Keine aktiven Quests',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),

          const SizedBox(height: 24),

          // Completed quests
          Text(
            'Abgeschlossen',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),

          ..._quests
              .where((q) => q.status == 'approved' || q.status == 'rejected' || q.status == 'pending_review')
              .take(10)
              .map((quest) => _QuestCard(
                    quest: quest,
                    statusColor: _statusColor(quest.status),
                    statusLabel: _statusLabel(quest.status),
                    categoryIcon: _categoryIcon(quest.templateCategory),
                    onTap: () => _openQuestDetail(quest),
                  )),
        ],
      ),
    );
  }

  void _openQuestDetail(QuestInstance quest) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => QuestDetailScreen(quest: quest),
      ),
    );
    // Refresh data when returning from detail screen
    _loadData();
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  const _StatItem({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _QuestCard extends StatelessWidget {
  final QuestInstance quest;
  final Color statusColor;
  final String statusLabel;
  final IconData categoryIcon;
  final VoidCallback onTap;

  const _QuestCard({
    required this.quest,
    required this.statusColor,
    required this.statusLabel,
    required this.categoryIcon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: statusColor.withAlpha(25),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(categoryIcon, color: statusColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      quest.templateName ?? 'Quest',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: statusColor.withAlpha(25),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            statusLabel,
                            style: TextStyle(
                              fontSize: 11,
                              color: statusColor,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        if (quest.rewardMinutes != null) ...[
                          const SizedBox(width: 8),
                          Icon(Icons.timer, size: 14,
                              color: theme.colorScheme.onSurfaceVariant),
                          const SizedBox(width: 2),
                          Text(
                            '+${quest.rewardMinutes} Min',
                            style: theme.textTheme.bodySmall,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right,
                  color: theme.colorScheme.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}
