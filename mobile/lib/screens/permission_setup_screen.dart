import 'dart:async';
import 'package:flutter/material.dart';
import '../services/agent_bridge.dart';

class PermissionSetupScreen extends StatefulWidget {
  const PermissionSetupScreen({super.key});

  @override
  State<PermissionSetupScreen> createState() => _PermissionSetupScreenState();
}

class _PermissionSetupScreenState extends State<PermissionSetupScreen> with WidgetsBindingObserver {
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
      _checkPermissions();  // Re-check when user returns from settings
    }
  }

  Future<void> _checkPermissions() async {
    setState(() => _loading = true);
    try {
      final perms = await AgentBridge.checkPermissions();
      setState(() {
        _permissions = perms;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  bool get _allGranted => _permissions.values.isNotEmpty && _permissions.values.every((v) => v);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final steps = [
      _PermissionStep(
        title: 'Bedienungshilfen',
        description: 'Erkennung der aktiven App',
        icon: Icons.accessibility_new,
        granted: _permissions['accessibility'] ?? false,
        onRequest: AgentBridge.requestAccessibility,
      ),
      _PermissionStep(
        title: 'Nutzungszugriff',
        description: 'App-Nutzungsstatistiken lesen',
        icon: Icons.bar_chart,
        granted: _permissions['usageStats'] ?? false,
        onRequest: AgentBridge.requestUsageStats,
      ),
      _PermissionStep(
        title: 'Geräte-Administrator',
        description: 'Schutz vor Deinstallation',
        icon: Icons.admin_panel_settings,
        granted: _permissions['deviceAdmin'] ?? false,
        onRequest: AgentBridge.requestDeviceAdmin,
      ),
      _PermissionStep(
        title: 'Über anderen Apps anzeigen',
        description: 'Sperrbildschirm bei Zeitüberschreitung',
        icon: Icons.layers,
        granted: _permissions['overlay'] ?? false,
        onRequest: AgentBridge.requestOverlay,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Heimdall einrichten'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Header
                Icon(Icons.shield, size: 64, color: theme.colorScheme.primary),
                const SizedBox(height: 16),
                Text(
                  'Berechtigungen einrichten',
                  style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  'Heimdall benötigt folgende Berechtigungen, um die Bildschirmzeit zu überwachen:',
                  style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),

                // Permission steps
                ...steps.map((step) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    leading: Icon(
                      step.icon,
                      color: step.granted ? Colors.green : theme.colorScheme.primary,
                    ),
                    title: Text(step.title),
                    subtitle: Text(step.description),
                    trailing: step.granted
                        ? const Icon(Icons.check_circle, color: Colors.green)
                        : FilledButton(
                            onPressed: step.onRequest,
                            child: const Text('Aktivieren'),
                          ),
                  ),
                )),

                const SizedBox(height: 24),

                // Start button
                if (_allGranted)
                  FilledButton.icon(
                    onPressed: () async {
                      await AgentBridge.startMonitoring();
                      if (context.mounted) Navigator.of(context).pop(true);
                    },
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Überwachung starten'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                    ),
                  )
                else
                  Text(
                    'Bitte alle Berechtigungen aktivieren',
                    style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.error),
                    textAlign: TextAlign.center,
                  ),
              ],
            ),
    );
  }
}

class _PermissionStep {
  final String title;
  final String description;
  final IconData icon;
  final bool granted;
  final Future<void> Function() onRequest;

  _PermissionStep({
    required this.title,
    required this.description,
    required this.icon,
    required this.granted,
    required this.onRequest,
  });
}
