import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class StatusScreen extends StatefulWidget {
  const StatusScreen({super.key});

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  Map<String, dynamic> _questStats = {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
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
      final stats = await api.getQuestStats(childId);

      if (mounted) {
        setState(() {
          _questStats = stats;
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
                _loadStatus();
              },
              child: const Text('Erneut versuchen'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadStatus,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Header
          Card(
            color: theme.colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Icon(Icons.shield,
                      size: 48, color: theme.colorScheme.onPrimaryContainer),
                  const SizedBox(height: 12),
                  Text(
                    'Dein Tagesstatus',
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Quest Stats
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Quest-Fortschritt',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _StatusRow(
                    icon: Icons.check_circle,
                    iconColor: Colors.green,
                    label: 'Quests erledigt heute',
                    value: '${_questStats['completed_today'] ?? 0} / ${_questStats['total_today'] ?? 0}',
                  ),
                  const SizedBox(height: 12),
                  // Progress bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: _questProgress,
                      minHeight: 8,
                      backgroundColor: theme.colorScheme.surfaceContainerHighest,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _StatusRow(
                    icon: Icons.timer,
                    iconColor: theme.colorScheme.primary,
                    label: 'Minuten verdient',
                    value: '${_questStats['minutes_earned_today'] ?? 0} Min',
                  ),
                  const SizedBox(height: 12),
                  _StatusRow(
                    icon: Icons.local_fire_department,
                    iconColor: Colors.orange,
                    label: 'Aktuelle Streak',
                    value: '${_questStats['current_streak'] ?? 0} Tage',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Streak motivation card
          if ((_questStats['current_streak'] ?? 0) > 0)
            Card(
              color: Colors.orange.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Text('🔥', style: TextStyle(fontSize: 32)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${_questStats['current_streak']} Tage in Folge!',
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.orange.shade800,
                            ),
                          ),
                          Text(
                            _streakMessage,
                            style: TextStyle(color: Colors.orange.shade700),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

          const SizedBox(height: 16),

          // Info card - device time budgets will come from agent
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bildschirmzeit',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.info_outline,
                            color: theme.colorScheme.onSurfaceVariant),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Die Anzeige der verbleibenden Bildschirmzeit ist verfügbar, sobald der Geräte-Agent installiert ist.',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  double get _questProgress {
    final completed = (_questStats['completed_today'] ?? 0) as int;
    final total = (_questStats['total_today'] ?? 0) as int;
    if (total == 0) return 0;
    return completed / total;
  }

  String get _streakMessage {
    final streak = (_questStats['current_streak'] ?? 0) as int;
    if (streak >= 5) return 'Super! Noch ${5 - (streak % 5)} Tage bis zum Wochen-Champion!';
    if (streak >= 3) return 'Weiter so! Du bist auf einem guten Weg!';
    return 'Mach weiter so!';
  }
}

class _StatusRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;

  const _StatusRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(icon, size: 22, color: iconColor),
        const SizedBox(width: 12),
        Expanded(
          child: Text(label, style: theme.textTheme.bodyMedium),
        ),
        Text(
          value,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
