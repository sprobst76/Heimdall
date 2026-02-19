import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../services/totp_service.dart';

class TotpUnlockScreen extends StatefulWidget {
  const TotpUnlockScreen({super.key});

  @override
  State<TotpUnlockScreen> createState() => _TotpUnlockScreenState();
}

class _TotpUnlockScreenState extends State<TotpUnlockScreen> {
  final _codeController = TextEditingController();
  String _mode = 'tan';
  bool _loading = false;
  bool _modeLoaded = false;

  late final TotpService _totpService;

  @override
  void initState() {
    super.initState();
    _totpService = TotpService();
    _loadCachedMode();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadCachedMode() async {
    final mode = await _totpService.getCachedMode();
    if (mounted) {
      setState(() {
        _mode = mode == 'both' ? 'tan' : mode;
        _modeLoaded = true;
      });
    }
  }

  Future<void> _unlock() async {
    final code = _codeController.text.trim();
    if (code.length != 6) return;

    final auth = context.read<AuthProvider>();
    final api = context.read<ApiService>();
    final childId = auth.childId;
    if (childId == null) return;

    setState(() => _loading = true);

    try {
      // Try offline verification first
      final offlineOk = await _totpService.verifyOffline(code);
      Map<String, dynamic> result;

      if (offlineOk) {
        // Validated offline — try to report to server (best-effort)
        try {
          result = await api.unlockTotp(childId, code, _mode);
        } catch (_) {
          // Server unavailable — use offline result
          final minutes = _mode == 'tan'
              ? await _totpService.getCachedTanMinutes()
              : await _totpService.getCachedOverrideMinutes();
          result = {'unlocked': true, 'mode': _mode, 'minutes': minutes};
        }
      } else {
        // No cached secret or offline check failed — try server
        result = await api.unlockTotp(childId, code, _mode);
      }

      if (mounted && result['unlocked'] == true) {
        final minutes = result['minutes'] as int;
        final mode = result['mode'] as String;
        final message = mode == 'override'
            ? 'Alle Sperren für $minutes Minuten aufgehoben!'
            : '+$minutes Minuten freigeschaltet!';

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 4),
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ungültiger Code: $e'),
            backgroundColor: Colors.red,
          ),
        );
        _codeController.clear();
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Eltern-Code eingeben'),
        backgroundColor: theme.colorScheme.surface,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 16),

            // Icon + description
            Icon(
              Icons.shield_outlined,
              size: 64,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              'Frag einen Elternteil nach dem\naktuellen 6-stelligen Code',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 32),

            // Mode selector (only shown when mode = 'both')
            if (_modeLoaded)
              FutureBuilder<String>(
                future: _totpService.getCachedMode(),
                builder: (context, snap) {
                  if (snap.data == 'both') {
                    return Column(
                      children: [
                        Text('Was möchtest du freischalten?',
                            style: theme.textTheme.bodyMedium),
                        const SizedBox(height: 8),
                        SegmentedButton<String>(
                          segments: const [
                            ButtonSegment(value: 'tan', label: Text('Bonus-Zeit')),
                            ButtonSegment(value: 'override', label: Text('Alle freischalten')),
                          ],
                          selected: {_mode},
                          onSelectionChanged: (v) => setState(() => _mode = v.first),
                        ),
                        const SizedBox(height: 24),
                      ],
                    );
                  }
                  return const SizedBox.shrink();
                },
              ),

            // Code input
            TextField(
              controller: _codeController,
              decoration: InputDecoration(
                labelText: '6-stelliger Code',
                hintText: '123456',
                prefixIcon: const Icon(Icons.lock_outline),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                counterText: '',
              ),
              keyboardType: TextInputType.number,
              maxLength: 6,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              textAlign: TextAlign.center,
              style: theme.textTheme.headlineMedium?.copyWith(
                letterSpacing: 8,
                fontWeight: FontWeight.bold,
              ),
              onSubmitted: (_) => _unlock(),
              autofocus: true,
            ),
            const SizedBox(height: 24),

            // Unlock button
            FilledButton.icon(
              onPressed: (_loading || _codeController.text.length != 6)
                  ? null
                  : _unlock,
              icon: _loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.lock_open),
              label: Text(_loading ? 'Prüfe...' : 'Freischalten'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),

            const SizedBox(height: 16),
            Text(
              'Der Code wechselt alle 30 Sekunden.\nFunktioniert auch ohne Internet.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
