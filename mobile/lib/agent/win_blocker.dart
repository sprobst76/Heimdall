/// Windows app blocker — terminates processes in blocked app-groups.
///
/// Analogous to the Python `AppBlocker` and the Android
/// `BlockingOverlayService`, but uses `dart:io` [Process.killPid]
/// for process termination.
library;

import 'dart:io' show Process, ProcessSignal;

import 'package:flutter/foundation.dart';

import 'win_monitor.dart';

/// Callback when a blocked app is killed.
typedef BlockActionCallback = void Function(
  String executable,
  String groupId,
);

/// Manages a set of blocked app-groups and terminates matching processes.
class WinBlocker {
  final Set<String> blockedGroups = {};

  /// Called after a process has been killed.
  BlockActionCallback? onBlockAction;

  void blockGroup(String groupId) {
    blockedGroups.add(groupId);
    debugPrint('WinBlocker: blocked group $groupId');
  }

  void unblockGroup(String groupId) {
    blockedGroups.remove(groupId);
    debugPrint('WinBlocker: unblocked group $groupId');
  }

  bool isBlocked(String? appGroupId) {
    if (appGroupId == null) return false;
    return blockedGroups.contains(appGroupId);
  }

  /// Enforce blocking on the current session.
  ///
  /// If the session's app-group is blocked, kill the process and fire
  /// the [onBlockAction] callback.
  void enforce(AppSession? session) {
    if (session == null) return;
    if (!isBlocked(session.appGroupId)) return;

    // Don't kill simulated processes or PID 0 (dummy)
    if (session.pid > 0 && session.pid != 99999) {
      _killProcess(session.pid, session.executable);
    }

    onBlockAction?.call(session.executable, session.appGroupId!);
  }

  void _killProcess(int pid, String executable) {
    try {
      final killed = Process.killPid(pid, ProcessSignal.sigterm);
      if (killed) {
        debugPrint('WinBlocker: killed $executable (PID $pid)');
      } else {
        debugPrint('WinBlocker: failed to kill $executable (PID $pid)');
      }
    } catch (e) {
      debugPrint('WinBlocker: error killing $executable: $e');
    }
  }
}
