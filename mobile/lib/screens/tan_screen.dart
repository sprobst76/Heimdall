import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/tan.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class TanScreen extends StatefulWidget {
  const TanScreen({super.key});

  @override
  State<TanScreen> createState() => _TanScreenState();
}

class _TanScreenState extends State<TanScreen> {
  List<Tan> _activeTans = [];
  List<Tan> _redeemedTans = [];
  bool _loading = true;
  String? _error;
  final _codeController = TextEditingController();
  bool _redeeming = false;

  @override
  void initState() {
    super.initState();
    _loadTans();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadTans() async {
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
        api.getTans(childId, status: 'active'),
        api.getTans(childId, status: 'redeemed'),
      ]);

      final active = (results[0])
          .map((t) => Tan.fromJson(t as Map<String, dynamic>))
          .toList();
      final redeemed = (results[1])
          .map((t) => Tan.fromJson(t as Map<String, dynamic>))
          .toList();

      if (mounted) {
        setState(() {
          _activeTans = active;
          _redeemedTans = redeemed;
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

  Future<void> _redeemTan() async {
    final code = _codeController.text.trim().toUpperCase();
    if (code.isEmpty) return;

    final auth = context.read<AuthProvider>();
    final api = context.read<ApiService>();
    final childId = auth.childId;
    if (childId == null) return;

    setState(() => _redeeming = true);

    try {
      await api.redeemTan(childId, code);
      _codeController.clear();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('TAN erfolgreich eingelöst!'),
            backgroundColor: Colors.green,
          ),
        );
      }

      await _loadTans();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Fehler: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _redeeming = false);
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
                _loadTans();
              },
              child: const Text('Erneut versuchen'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadTans,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // TAN input section
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TAN einlösen',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _codeController,
                          decoration: const InputDecoration(
                            hintText: 'z.B. HERO-7749',
                            prefixIcon: Icon(Icons.confirmation_number),
                            border: OutlineInputBorder(),
                          ),
                          textCapitalization: TextCapitalization.characters,
                          inputFormatters: [
                            FilteringTextInputFormatter.allow(
                              RegExp(r'[A-Za-z0-9\-]'),
                            ),
                          ],
                          onSubmitted: (_) => _redeemTan(),
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton(
                        onPressed: _redeeming ? null : _redeemTan,
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 18,
                          ),
                        ),
                        child: _redeeming
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Einlösen'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Active TANs
          Text(
            'Aktive TANs',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),

          if (_activeTans.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Icon(Icons.confirmation_number_outlined,
                        size: 48, color: theme.colorScheme.onSurfaceVariant),
                    const SizedBox(height: 8),
                    Text(
                      'Keine aktiven TANs',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Erledige Quests um TANs zu verdienen!',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            ..._activeTans.map((tan) => _TanCard(tan: tan, isActive: true)),

          const SizedBox(height: 24),

          // Redeemed TANs
          if (_redeemedTans.isNotEmpty) ...[
            Text(
              'Eingelöste TANs',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            ..._redeemedTans.take(10).map(
                  (tan) => _TanCard(tan: tan, isActive: false),
                ),
          ],
        ],
      ),
    );
  }
}

class _TanCard extends StatelessWidget {
  final Tan tan;
  final bool isActive;

  const _TanCard({required this.tan, required this.isActive});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isActive
                    ? theme.colorScheme.primary.withAlpha(25)
                    : Colors.grey.withAlpha(25),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.confirmation_number,
                color: isActive ? theme.colorScheme.primary : Colors.grey,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tan.code,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      fontFamily: 'monospace',
                      color: isActive ? null : Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      if (tan.valueMinutes != null) ...[
                        Icon(Icons.timer, size: 14,
                            color: theme.colorScheme.onSurfaceVariant),
                        const SizedBox(width: 2),
                        Text(
                          '+${tan.valueMinutes} Min',
                          style: theme.textTheme.bodySmall,
                        ),
                        const SizedBox(width: 8),
                      ],
                      if (tan.source != null) ...[
                        Icon(
                          tan.source == 'quest'
                              ? Icons.emoji_events
                              : Icons.person,
                          size: 14,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 2),
                        Text(
                          tan.source == 'quest' ? 'Quest' : 'Eltern',
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            if (isActive)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green.withAlpha(25),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Aktiv',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.green,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              )
            else
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.grey.withAlpha(25),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Eingelöst',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
