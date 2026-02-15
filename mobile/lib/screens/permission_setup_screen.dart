import 'dart:async';
import 'package:flutter/material.dart';
import '../services/agent_bridge.dart';

class PermissionSetupScreen extends StatefulWidget {
  const PermissionSetupScreen({super.key});

  @override
  State<PermissionSetupScreen> createState() => _PermissionSetupScreenState();
}

class _PermissionSetupScreenState extends State<PermissionSetupScreen>
    with WidgetsBindingObserver {
  Map<String, bool> _permissions = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkPermissions();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _checkPermissions();
    }
  }

  Future<void> _checkPermissions() async {
    try {
      final perms = await AgentBridge.checkPermissions();
      if (mounted) {
        setState(() {
          _permissions = perms;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  int get _grantedCount =>
      _permissions.values.where((v) => v).length;

  bool get _criticalGranted =>
      (_permissions['accessibility'] ?? false) &&
      (_permissions['overlay'] ?? false);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final totalSteps = 4;

    final steps = [
      _PermissionStep(
        number: 1,
        title: 'Bedienungshilfen',
        description:
            'Heimdall muss erkennen können, welche App gerade im Vordergrund ist. '
            'Dazu wird der Bedienungshilfen-Dienst benötigt.',
        icon: Icons.accessibility_new,
        granted: _permissions['accessibility'] ?? false,
        critical: true,
        onRequest: AgentBridge.requestAccessibility,
      ),
      _PermissionStep(
        number: 2,
        title: 'Über anderen Apps anzeigen',
        description:
            'Wenn eine gesperrte App geöffnet wird, zeigt Heimdall einen '
            'Sperrbildschirm darüber an. Dafür ist die Overlay-Berechtigung nötig.',
        icon: Icons.layers,
        granted: _permissions['overlay'] ?? false,
        critical: true,
        onRequest: AgentBridge.requestOverlay,
      ),
      _PermissionStep(
        number: 3,
        title: 'Nutzungszugriff',
        description:
            'Ermöglicht Heimdall, die tägliche Bildschirmzeit pro App zu messen '
            'und Statistiken anzuzeigen.',
        icon: Icons.bar_chart,
        granted: _permissions['usageStats'] ?? false,
        critical: false,
        onRequest: AgentBridge.requestUsageStats,
      ),
      _PermissionStep(
        number: 4,
        title: 'Geräte-Administrator',
        description:
            'Schützt die Heimdall-App vor Deinstallation durch das Kind.',
        icon: Icons.admin_panel_settings,
        granted: _permissions['deviceAdmin'] ?? false,
        critical: false,
        onRequest: AgentBridge.requestDeviceAdmin,
      ),
    ];

    return Scaffold(
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: Column(
                children: [
                  // Progress header
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
                    child: Column(
                      children: [
                        Icon(Icons.shield,
                            size: 56, color: theme.colorScheme.primary),
                        const SizedBox(height: 12),
                        Text(
                          'Heimdall einrichten',
                          style: theme.textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '$_grantedCount von $totalSteps Berechtigungen erteilt',
                          style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant),
                        ),
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: _grantedCount / totalSteps,
                            minHeight: 6,
                            backgroundColor:
                                theme.colorScheme.surfaceContainerHighest,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Permission list
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: steps.length,
                      itemBuilder: (context, index) {
                        final step = steps[index];
                        return _PermissionCard(step: step, theme: theme);
                      },
                    ),
                  ),

                  // Bottom buttons
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    child: Column(
                      children: [
                        FilledButton.icon(
                          onPressed: _criticalGranted
                              ? () async {
                                  await AgentBridge.startMonitoring();
                                  if (context.mounted) {
                                    Navigator.of(context).pop(true);
                                  }
                                }
                              : null,
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Überwachung starten'),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size.fromHeight(48),
                          ),
                        ),
                        if (!_criticalGranted) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Bedienungshilfen und Overlay sind Pflicht',
                            style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant),
                          ),
                        ],
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(false),
                          child: const Text('Später einrichten'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _PermissionCard extends StatelessWidget {
  final _PermissionStep step;
  final ThemeData theme;

  const _PermissionCard({required this.step, required this.theme});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Step number circle
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: step.granted
                    ? Colors.green
                    : step.critical
                        ? theme.colorScheme.primary
                        : theme.colorScheme.surfaceContainerHighest,
              ),
              child: Center(
                child: step.granted
                    ? const Icon(Icons.check, color: Colors.white, size: 20)
                    : Text(
                        '${step.number}',
                        style: TextStyle(
                          color: step.critical
                              ? theme.colorScheme.onPrimary
                              : theme.colorScheme.onSurfaceVariant,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
              ),
            ),
            const SizedBox(width: 12),
            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          step.title,
                          style: theme.textTheme.titleSmall
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ),
                      if (step.critical && !step.granted)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.errorContainer,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'Pflicht',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: theme.colorScheme.onErrorContainer,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    step.description,
                    style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant),
                  ),
                  if (!step.granted) ...[
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 32,
                      child: FilledButton.tonal(
                        onPressed: step.onRequest,
                        child: const Text('Aktivieren'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PermissionStep {
  final int number;
  final String title;
  final String description;
  final IconData icon;
  final bool granted;
  final bool critical;
  final Future<void> Function() onRequest;

  _PermissionStep({
    required this.number,
    required this.title,
    required this.description,
    required this.icon,
    required this.granted,
    required this.critical,
    required this.onRequest,
  });
}
