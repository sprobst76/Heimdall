import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../models/quest.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class QuestDetailScreen extends StatefulWidget {
  final QuestInstance quest;

  const QuestDetailScreen({super.key, required this.quest});

  @override
  State<QuestDetailScreen> createState() => _QuestDetailScreenState();
}

class _QuestDetailScreenState extends State<QuestDetailScreen> {
  late QuestInstance _quest;
  bool _actionLoading = false;
  String? _successMessage;

  @override
  void initState() {
    super.initState();
    _quest = widget.quest;
  }

  Future<void> _claimQuest() async {
    final auth = context.read<AuthProvider>();
    final api = context.read<ApiService>();
    final childId = auth.childId;
    if (childId == null) return;

    setState(() => _actionLoading = true);

    try {
      final data = await api.claimQuest(childId, _quest.id);
      final updated = QuestInstance.fromJson(data);
      updated.templateName = _quest.templateName;
      updated.templateCategory = _quest.templateCategory;
      updated.rewardMinutes = _quest.rewardMinutes;
      updated.proofType = _quest.proofType;

      setState(() {
        _quest = updated;
        _actionLoading = false;
        _successMessage = 'Quest angenommen!';
      });
    } catch (e) {
      setState(() => _actionLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Fehler: $e')),
        );
      }
    }
  }

  Future<void> _submitProof() async {
    final auth = context.read<AuthProvider>();
    final api = context.read<ApiService>();
    final childId = auth.childId;
    if (childId == null) return;

    final picker = ImagePicker();
    final image = await picker.pickImage(
      source: ImageSource.camera,
      maxWidth: 1920,
      maxHeight: 1920,
      imageQuality: 85,
    );

    if (image == null) return;

    setState(() => _actionLoading = true);

    try {
      final uploadResult = await api.uploadProof(image.path);
      final proofUrl = uploadResult['url'] as String;

      final data = await api.submitProof(
        childId,
        _quest.id,
        _quest.proofType ?? 'photo',
        proofUrl,
      );

      final updated = QuestInstance.fromJson(data);
      updated.templateName = _quest.templateName;
      updated.templateCategory = _quest.templateCategory;
      updated.rewardMinutes = _quest.rewardMinutes;
      updated.proofType = _quest.proofType;

      setState(() {
        _quest = updated;
        _actionLoading = false;
        _successMessage = 'Nachweis eingereicht! Warte auf Prüfung.';
      });
    } catch (e) {
      setState(() => _actionLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Fehler beim Hochladen: $e')),
        );
      }
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

  String _proofTypeLabel(String type) {
    switch (type) {
      case 'photo':
        return 'Foto';
      case 'screenshot':
        return 'Screenshot';
      case 'parent_confirm':
        return 'Eltern-Bestätigung';
      case 'auto':
        return 'Automatisch';
      case 'checklist':
        return 'Checkliste';
      default:
        return type;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(_quest.templateName ?? 'Quest'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Quest info card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _categoryIcon(_quest.templateCategory),
                          size: 32,
                          color: theme.colorScheme.primary,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _quest.templateName ?? 'Quest',
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              if (_quest.templateCategory != null)
                                Text(
                                  _quest.templateCategory!,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(),
                    const SizedBox(height: 16),

                    // Status
                    _InfoRow(
                      icon: Icons.info_outline,
                      label: 'Status',
                      value: _statusLabel(_quest.status),
                      valueColor: _statusColor(_quest.status),
                    ),
                    const SizedBox(height: 12),

                    // Reward
                    if (_quest.rewardMinutes != null) ...[
                      _InfoRow(
                        icon: Icons.timer,
                        label: 'Belohnung',
                        value: '+${_quest.rewardMinutes} Minuten',
                        valueColor: theme.colorScheme.primary,
                      ),
                      const SizedBox(height: 12),
                    ],

                    // Proof type
                    if (_quest.proofType != null)
                      _InfoRow(
                        icon: Icons.camera_alt_outlined,
                        label: 'Nachweis',
                        value: _proofTypeLabel(_quest.proofType!),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Success message
            if (_successMessage != null) ...[
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green.shade700),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _successMessage!,
                          style: TextStyle(color: Colors.green.shade700),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Action buttons based on status
            if (_quest.status == 'available')
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _actionLoading ? null : _claimQuest,
                  icon: _actionLoading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.emoji_events),
                  label: const Text('Quest annehmen'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),

            if (_quest.status == 'claimed')
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _actionLoading ? null : _submitProof,
                  icon: _actionLoading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.camera_alt),
                  label: const Text('Nachweis einreichen'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),

            if (_quest.status == 'pending_review')
              Card(
                color: Colors.orange.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.hourglass_top, color: Colors.orange.shade700),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                          'Nachweis wird geprüft. Bitte warte auf die Bestätigung.',
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            if (_quest.status == 'approved')
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Icon(Icons.check_circle,
                          color: Colors.green.shade700, size: 48),
                      const SizedBox(height: 8),
                      Text(
                        'Quest erledigt!',
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: Colors.green.shade700,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (_quest.rewardMinutes != null)
                        Text(
                          '+${_quest.rewardMinutes} Minuten verdient',
                          style: TextStyle(color: Colors.green.shade700),
                        ),
                    ],
                  ),
                ),
              ),

            if (_quest.status == 'rejected')
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.cancel, color: Colors.red.shade700),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                          'Quest wurde abgelehnt. Versuche es erneut!',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(icon, size: 20, color: theme.colorScheme.onSurfaceVariant),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: valueColor,
          ),
        ),
      ],
    );
  }
}
