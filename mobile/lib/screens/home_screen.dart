import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:window_manager/window_manager.dart';
import '../providers/auth_provider.dart';
import '../services/agent_bridge.dart';
import 'quest_overview_screen.dart';
import 'tan_screen.dart';
import 'status_screen.dart';
import 'chat_screen.dart';
import 'blocking_overlay_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;
  bool _overlayShown = false;
  bool _lockdownShown = false;
  bool _tamperDialogShown = false;
  bool _vpnDialogShown = false;
  bool _installDialogShown = false;

  final _screens = const [
    QuestOverviewScreen(),
    TanScreen(),
    StatusScreen(),
    ChatScreen(),
  ];

  @override
  void initState() {
    super.initState();
    AgentBridge.onLimitWarning = _handleLimitWarning;
    AgentBridge.onTamperDetected = _handleTamperDetected;
    AgentBridge.onVpnDetected = _handleVpnDetected;
    AgentBridge.onPackageInstalled = _handlePackageInstalled;
    if (Platform.isWindows) {
      AgentBridge.onBlockTriggered = _handleBlockTriggered;
      // Wire up full lockdown callbacks
      final service = AgentBridge.windowsBridge?.service;
      if (service != null) {
        service.onFullLockdown = _handleFullLockdown;
        service.onFullLockdownEnd = _handleFullLockdownEnd;
      }
    }
  }

  @override
  void dispose() {
    AgentBridge.onLimitWarning = null;
    AgentBridge.onTamperDetected = null;
    AgentBridge.onVpnDetected = null;
    AgentBridge.onPackageInstalled = null;
    if (Platform.isWindows) {
      AgentBridge.onBlockTriggered = null;
      final service = AgentBridge.windowsBridge?.service;
      if (service != null) {
        service.onFullLockdown = null;
        service.onFullLockdownEnd = null;
      }
    }
    super.dispose();
  }

  void _handleBlockTriggered(String executable, String groupId) {
    if (_overlayShown || _lockdownShown || !mounted) return;
    _overlayShown = true;

    // Lookup group info from WinAgentService
    final bridge = AgentBridge.windowsBridge;
    final limits = bridge?.service.groupLimits.value ?? [];
    final gl = limits.where((g) => g.appGroupId == groupId).firstOrNull;

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => BlockingOverlayScreen(
          appName: executable,
          groupName: gl?.groupName ?? groupId,
          usedMinutes: gl?.usedMinutes ?? 0,
          limitMinutes: gl?.limitMinutes ?? 0,
          onDismiss: () {
            _overlayShown = false;
            Navigator.of(context).pop();
          },
        ),
      ),
    );
  }

  void _handleLimitWarning(String groupId, int remainingMinutes) {
    if (!mounted) return;
    final label = remainingMinutes == 1 ? '1 Minute' : '$remainingMinutes Minuten';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        duration: const Duration(seconds: 8),
        backgroundColor: const Color(0xFFF59E0B), // amber-500
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        content: Row(
          children: [
            const Icon(Icons.timer_outlined, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Noch $label Bildschirmzeit!',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        action: SnackBarAction(
          label: 'OK',
          textColor: Colors.white,
          onPressed: () =>
              ScaffoldMessenger.of(context).hideCurrentSnackBar(),
        ),
      ),
    );
  }

  void _handleTamperDetected(String reason) {
    if (_tamperDialogShown || !mounted) return;
    _tamperDialogShown = true;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.security, color: Color(0xFFEF4444), size: 40),
        title: const Text(
          'Schutz unterbrochen',
          textAlign: TextAlign.center,
        ),
        content: const Text(
          'Der Heimdall-Schutz wurde kurz deaktiviert.\n\n'
          'Deine Eltern wurden bereits benachrichtigt.',
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          FilledButton(
            onPressed: () {
              _tamperDialogShown = false;
              Navigator.of(ctx).pop();
            },
            child: const Text('Verstanden'),
          ),
        ],
      ),
    );
  }

  void _handleVpnDetected(String reason) {
    if (_vpnDialogShown || !mounted) return;
    _vpnDialogShown = true;
    final label = reason == 'proxy' ? 'Proxy' : 'VPN';
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.vpn_lock, color: Color(0xFFEF4444), size: 40),
        title: Text(
          '$label erkannt',
          textAlign: TextAlign.center,
        ),
        content: Text(
          'Ein $label wurde auf diesem Gerät aktiviert.\n\n'
          'Deine Eltern wurden benachrichtigt.',
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          FilledButton(
            onPressed: () {
              _vpnDialogShown = false;
              Navigator.of(ctx).pop();
            },
            child: const Text('Verstanden'),
          ),
        ],
      ),
    );
  }

  void _handlePackageInstalled(String packageName) {
    if (_installDialogShown || !mounted) return;
    _installDialogShown = true;
    // Show short app name (last segment of package name)
    final appLabel = packageName.split('.').last;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.install_mobile, color: Color(0xFFF59E0B), size: 40),
        title: const Text(
          'Neue App installiert',
          textAlign: TextAlign.center,
        ),
        content: Text(
          'Die App "$appLabel" wurde installiert und ist gesperrt,\n'
          'bis deine Eltern sie freigeben.',
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          OutlinedButton(
            onPressed: () {
              _installDialogShown = false;
              Navigator.of(ctx).pop();
            },
            child: const Text('OK'),
          ),
        ],
      ),
    ).then((_) => _installDialogShown = false);
  }

  void _handleFullLockdown(int durationSeconds) {
    if (_lockdownShown || !mounted) return;
    _lockdownShown = true;

    // Go fullscreen + always on top
    _setFullscreen(true);

    // Pop any existing overlay first
    if (_overlayShown) {
      _overlayShown = false;
      Navigator.of(context).pop();
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => FullLockdownScreen(
          durationSeconds: durationSeconds,
          onFinished: _endFullLockdown,
        ),
      ),
    );
  }

  void _handleFullLockdownEnd() {
    _endFullLockdown();
  }

  void _endFullLockdown() {
    if (!_lockdownShown) return;
    _lockdownShown = false;
    _setFullscreen(false);
    if (mounted) {
      Navigator.of(context).pop();
    }
    // Also stop the service-side lockdown if still active
    AgentBridge.windowsBridge?.service.stopFullLockdown();
  }

  Future<void> _setFullscreen(bool fullscreen) async {
    if (!Platform.isWindows) return;
    try {
      await windowManager.setAlwaysOnTop(fullscreen);
      await windowManager.setFullScreen(fullscreen);
    } catch (e) {
      debugPrint('HomeScreen: window_manager error: $e');
    }
  }

  void _triggerDemoLockdown() {
    AgentBridge.windowsBridge?.service.startFullLockdown(durationSeconds: 30);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.shield, color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            const Text('HEIMDALL'),
          ],
        ),
        actions: [
          // Demo: Vollsperrung button (only on Windows)
          if (Platform.isWindows)
            IconButton(
              icon: const Icon(Icons.lock),
              tooltip: 'Vollsperrung testen (30s)',
              onPressed: _triggerDemoLockdown,
            ),
          if (auth.childName != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Center(
                child: Text(
                  auth.childName!,
                  style: theme.textTheme.bodyMedium,
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Abmelden',
            onPressed: () async {
              await auth.logout();
            },
          ),
        ],
      ),
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.emoji_events_outlined),
            selectedIcon: Icon(Icons.emoji_events),
            label: 'Quests',
          ),
          NavigationDestination(
            icon: Icon(Icons.confirmation_number_outlined),
            selectedIcon: Icon(Icons.confirmation_number),
            label: 'TANs',
          ),
          NavigationDestination(
            icon: Icon(Icons.timer_outlined),
            selectedIcon: Icon(Icons.timer),
            label: 'Status',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Fragen',
          ),
        ],
      ),
    );
  }
}
