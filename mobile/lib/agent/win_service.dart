/// Windows Agent orchestrator — wires monitor, blocker, and tray together.
///
/// Manages app-group mappings, rules, and the polling loop.
/// Supports a demo mode with hardcoded rules (no backend required).
library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'win_monitor.dart';
import 'win_blocker.dart';

/// Demo app-group mappings: executable (lowercase) → groupId.
const kDemoAppGroupMap = <String, String>{
  // Gaming (easy to test on any PC)
  'notepad.exe': 'gaming',
  'calc.exe': 'gaming',
  'calculatorapp.exe': 'gaming',
  'minesweeper.exe': 'gaming',
  'solitaire.exe': 'gaming',
  // Browser
  'chrome.exe': 'browser',
  'firefox.exe': 'browser',
  'msedge.exe': 'browser',
  // Streaming
  'spotify.exe': 'streaming',
  'vlc.exe': 'streaming',
  // Productivity (not blocked)
  'code.exe': 'productivity',
  'winword.exe': 'productivity',
  'excel.exe': 'productivity',
};

/// A group-limit entry from the rules.
class GroupLimit {
  final String appGroupId;
  final String groupName;
  final int limitMinutes;
  int usedMinutes;

  GroupLimit({
    required this.appGroupId,
    required this.groupName,
    required this.limitMinutes,
    this.usedMinutes = 0,
  });

  int get remainingMinutes => (limitMinutes - usedMinutes).clamp(0, limitMinutes);
  bool get isExceeded => limitMinutes > 0 && usedMinutes >= limitMinutes;
}

/// Demo rules with realistic values.
List<GroupLimit> createDemoRules() => [
      GroupLimit(
        appGroupId: 'gaming',
        groupName: 'Spiele',
        limitMinutes: 60,
        usedMinutes: 60, // limit reached → blocked
      ),
      GroupLimit(
        appGroupId: 'browser',
        groupName: 'Browser',
        limitMinutes: 30,
        usedMinutes: 30, // limit reached → blocked
      ),
      GroupLimit(
        appGroupId: 'streaming',
        groupName: 'Streaming',
        limitMinutes: 45,
        usedMinutes: 0,
      ),
      GroupLimit(
        appGroupId: 'productivity',
        groupName: 'Produktivität',
        limitMinutes: 999,
        usedMinutes: 0,
      ),
    ];

/// Agent status for tray icon color.
enum AgentStatus { connected, warning, blocked, offline }

/// Callback when a blocked app is detected (show overlay).
typedef BlockTriggeredCallback = void Function(
  String executable,
  String groupId,
  String groupName,
  int usedMinutes,
  int limitMinutes,
);

/// Central Windows agent service.
class WinAgentService {
  WinMonitor _monitor;
  late final WinBlocker _blocker;

  Map<String, String> _appGroupMap;
  List<GroupLimit> _groupLimits = [];
  bool _running = false;

  /// Current agent status.
  final ValueNotifier<AgentStatus> status =
      ValueNotifier(AgentStatus.offline);

  /// Current group times for UI display.
  final ValueNotifier<List<GroupLimit>> groupLimits = ValueNotifier([]);

  /// Called when a blocked app is detected.
  BlockTriggeredCallback? onBlockTriggered;

  /// Called when foreground app changes (for status screen).
  void Function(AppSession? session)? onAppChanged;

  WinAgentService({
    Map<String, String>? appGroupMap,
  })  : _appGroupMap = appGroupMap ?? {},
        _monitor = WinMonitor(
          appGroupMap: appGroupMap ?? {},
          onAppChange: _dummyAppChange,
        ) {
    _blocker = WinBlocker();
    _monitor = WinMonitor(
      appGroupMap: _appGroupMap,
      onAppChange: _handleAppChange,
    );
    _blocker.onBlockAction = _handleBlockAction;
  }

  // Placeholder für initializer list (wird sofort überschrieben)
  static void _dummyAppChange(AppSession? a, AppSession? b) {}

  WinMonitor get monitor => _monitor;
  WinBlocker get blocker => _blocker;
  bool get isRunning => _running;

  /// Start monitoring with demo rules (no backend).
  void startDemo() {
    _appGroupMap = Map.of(kDemoAppGroupMap);
    _monitor = WinMonitor(
      appGroupMap: _appGroupMap,
      onAppChange: _handleAppChange,
    );
    applyRules(createDemoRules());
    start();
  }

  /// Start the monitoring loop.
  void start() {
    if (_running) return;
    _running = true;
    _monitor.start();
    _updateStatus();
    debugPrint('WinAgentService: started');
  }

  /// Stop the monitoring loop.
  void stop() {
    _running = false;
    _monitor.stop();
    status.value = AgentStatus.offline;
    debugPrint('WinAgentService: stopped');
  }

  /// Apply rules (from backend or demo).
  void applyRules(List<GroupLimit> limits) {
    _groupLimits = limits;
    groupLimits.value = List.of(limits);

    // Update blocked groups based on limits
    for (final gl in limits) {
      if (gl.isExceeded) {
        _blocker.blockGroup(gl.appGroupId);
      } else {
        _blocker.unblockGroup(gl.appGroupId);
      }
    }

    _updateStatus();
  }

  /// Block a group manually.
  void blockGroup(String groupId) {
    _blocker.blockGroup(groupId);
    _updateStatus();
    // Immediately enforce
    _blocker.enforce(_monitor.currentSession);
  }

  /// Unblock a group manually.
  void unblockGroup(String groupId) {
    _blocker.unblockGroup(groupId);
    _updateStatus();
  }

  /// Get usage by group (used/limit minutes).
  Map<String, int> getUsageToday() {
    final result = <String, int>{};
    for (final gl in _groupLimits) {
      result[gl.appGroupId] = gl.usedMinutes;
    }
    return result;
  }

  // -- Internal callbacks --

  void _handleAppChange(AppSession? oldSession, AppSession? newSession) {
    onAppChanged?.call(newSession);

    // Enforce blocking on the new session
    if (newSession != null) {
      _blocker.enforce(newSession);
    }
  }

  void _handleBlockAction(String executable, String groupId) {
    debugPrint('WinAgentService: blocked $executable (group: $groupId)');

    // Find group info
    final gl = _groupLimits.where((g) => g.appGroupId == groupId).firstOrNull;

    onBlockTriggered?.call(
      executable,
      groupId,
      gl?.groupName ?? groupId,
      gl?.usedMinutes ?? 0,
      gl?.limitMinutes ?? 0,
    );
  }

  void _updateStatus() {
    if (!_running) {
      status.value = AgentStatus.offline;
      return;
    }

    if (_blocker.blockedGroups.isNotEmpty) {
      status.value = AgentStatus.blocked;
    } else if (_groupLimits.any((g) => g.remainingMinutes <= 5 && g.limitMinutes > 0 && g.limitMinutes < 999)) {
      status.value = AgentStatus.warning;
    } else {
      status.value = AgentStatus.connected;
    }
  }
}
