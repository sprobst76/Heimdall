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

  final _screens = const [
    QuestOverviewScreen(),
    TanScreen(),
    StatusScreen(),
    ChatScreen(),
  ];

  @override
  void initState() {
    super.initState();
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
