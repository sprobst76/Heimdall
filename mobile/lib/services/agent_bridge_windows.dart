/// Windows-specific agent bridge implementation.
///
/// Runs the agent directly in Dart using the win32 package — no separate
/// Python process, no MethodChannel. This is imported by [AgentBridge]
/// and used when [Platform.isWindows] is true.
library;

import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:launch_at_startup/launch_at_startup.dart';

import '../agent/win_service.dart';
import '../agent/win_monitor.dart';

class WindowsAgentBridge {
  final WinAgentService _service = WinAgentService();

  // Callbacks (wired from AgentBridge)
  void Function(String executable)? onAppChanged;
  void Function(String executable, String groupId)? onBlockTriggered;

  WindowsAgentBridge() {
    _service.onAppChanged = (session) {
      if (session != null) {
        onAppChanged?.call(session.executable);
      }
    };
    _service.onBlockTriggered = (exe, groupId, groupName, used, limit) {
      onBlockTriggered?.call(exe, groupId);
    };
  }

  /// Access the underlying agent service (for status screen, tray, etc.).
  WinAgentService get service => _service;

  // -- Monitoring --

  bool startMonitoring() {
    _service.startDemo();
    return true;
  }

  bool stopMonitoring() {
    _service.stop();
    return true;
  }

  bool isMonitoringActive() => _service.isRunning;

  // -- Permissions --

  Future<Map<String, bool>> checkPermissions() async {
    if (!Platform.isWindows) {
      // On non-Windows dev machines, pretend all OK
      return {'autostart': true, 'monitoring': true};
    }

    final autostartEnabled = await launchAtStartup.isEnabled();

    return {
      'autostart': autostartEnabled,
      'monitoring': true, // always available on Windows
    };
  }

  Future<void> requestAutostart() async {
    if (!Platform.isWindows) return;

    launchAtStartup.setup(
      appName: 'Heimdall Kind',
      appPath: Platform.resolvedExecutable,
    );
    await launchAtStartup.enable();
    debugPrint('WindowsAgentBridge: autostart enabled');
  }

  // -- Blocking --

  void blockGroup(String groupId) => _service.blockGroup(groupId);

  void unblockGroup(String groupId) => _service.unblockGroup(groupId);

  // -- Data --

  Map<String, int> getUsageToday() => _service.getUsageToday();
}
