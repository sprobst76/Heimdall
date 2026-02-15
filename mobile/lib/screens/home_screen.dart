import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
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
    }
  }

  @override
  void dispose() {
    if (Platform.isWindows) {
      AgentBridge.onBlockTriggered = null;
    }
    super.dispose();
  }

  void _handleBlockTriggered(String executable, String groupId) {
    if (_overlayShown || !mounted) return;
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
