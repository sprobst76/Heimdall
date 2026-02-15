/// Windows foreground-app monitor using win32 APIs.
///
/// Polls [GetForegroundWindow] at a fixed interval and fires a callback
/// when the active application changes. On non-Windows platforms a dummy
/// implementation is used for development.
library;

import 'dart:async';
import 'dart:io' show Platform, Process;

import 'package:flutter/foundation.dart';

// win32 imports — only used on Windows
import 'package:win32/win32.dart' as win32;
import 'dart:ffi';
import 'package:ffi/ffi.dart';

/// Represents an active foreground-app session.
class AppSession {
  final String executable; // e.g. "notepad.exe"
  final String windowTitle;
  final String? appGroupId; // mapped from config
  final int pid;
  final DateTime startedAt;

  const AppSession({
    required this.executable,
    required this.windowTitle,
    this.appGroupId,
    required this.pid,
    required this.startedAt,
  });
}

/// Callback signature when the foreground app changes.
typedef AppChangeCallback = void Function(
  AppSession? oldSession,
  AppSession? newSession,
);

/// Monitors the active foreground window on Windows.
class WinMonitor {
  final Duration pollInterval;
  final Map<String, String> appGroupMap; // executable (lowercase) → groupId
  final AppChangeCallback onAppChange;

  AppSession? _currentSession;
  Timer? _timer;

  // For simulation / remote testing
  _SimulatedApp? _simulated;

  WinMonitor({
    this.pollInterval = const Duration(seconds: 2),
    required this.appGroupMap,
    required this.onAppChange,
  });

  /// The currently tracked foreground session.
  AppSession? get currentSession => _currentSession;

  /// Start polling.
  void start() {
    _timer?.cancel();
    _timer = Timer.periodic(pollInterval, (_) => poll());
    debugPrint('WinMonitor: started (interval=${pollInterval.inSeconds}s)');
  }

  /// Stop polling.
  void stop() {
    _timer?.cancel();
    _timer = null;
    debugPrint('WinMonitor: stopped');
  }

  /// Inject a simulated foreground app (for remote testing).
  void simulateForeground(String executable, {String title = 'Simulated'}) {
    _simulated = _SimulatedApp(executable, title, 99999);
    debugPrint('WinMonitor: simulating $executable');
    poll(); // trigger immediately
  }

  /// Clear simulation.
  void clearSimulation() {
    _simulated = null;
    debugPrint('WinMonitor: simulation cleared');
  }

  /// Single poll iteration.
  void poll() {
    final fg = _getForegroundApp();
    if (fg == null) {
      if (_currentSession != null) {
        final old = _currentSession;
        _currentSession = null;
        onAppChange(old, null);
      }
      return;
    }

    final (executable, windowTitle, pid) = fg;

    // Same app, same process → nothing to do
    if (_currentSession != null &&
        _currentSession!.executable == executable &&
        _currentSession!.pid == pid) {
      return;
    }

    final oldSession = _currentSession;
    final groupId = appGroupMap[executable.toLowerCase()];

    final newSession = AppSession(
      executable: executable,
      windowTitle: windowTitle,
      appGroupId: groupId,
      pid: pid,
      startedAt: DateTime.now(),
    );

    _currentSession = newSession;
    debugPrint('WinMonitor: ${oldSession?.executable} → $executable (group=$groupId)');
    onAppChange(oldSession, newSession);
  }

  /// Detect the foreground app. Returns (executable, title, pid) or null.
  (String, String, int)? _getForegroundApp() {
    // Simulation takes priority
    if (_simulated != null) {
      return (_simulated!.exe, _simulated!.title, _simulated!.pid);
    }

    if (!Platform.isWindows) {
      // Dummy for Linux/macOS development
      return ('dummy.exe', 'Dummy Window', 0);
    }

    return _detectForegroundWindows();
  }

  /// Real Windows detection via win32 APIs.
  static (String, String, int)? _detectForegroundWindows() {
    try {
      final hwnd = win32.GetForegroundWindow();
      if (hwnd == 0) return null;

      // Window title
      final titleBuf = calloc<Uint16>(256);
      final titlePtr = titleBuf.cast<Utf16>();
      win32.GetWindowText(hwnd, titlePtr, 256);
      final windowTitle = titlePtr.toDartString();
      calloc.free(titleBuf);

      // PID
      final pidPtr = calloc<Uint32>();
      win32.GetWindowThreadProcessId(hwnd, pidPtr);
      final pid = pidPtr.value;
      calloc.free(pidPtr);
      if (pid <= 0) return null;

      // Executable name via process handle
      final hProcess = win32.OpenProcess(
        win32.PROCESS_QUERY_INFORMATION | win32.PROCESS_VM_READ,
        win32.FALSE,
        pid,
      );
      if (hProcess == 0) return null;

      final exeBuf = calloc<Uint16>(win32.MAX_PATH);
      final exePtr = exeBuf.cast<Utf16>();
      final len = win32.GetModuleFileNameEx(hProcess, 0, exePtr, win32.MAX_PATH);
      win32.CloseHandle(hProcess);

      if (len == 0) {
        calloc.free(exeBuf);
        return null;
      }

      final fullPath = exePtr.toDartString();
      calloc.free(exeBuf);

      // Extract just the filename
      final executable = fullPath.split('\\').last;

      return (executable, windowTitle, pid);
    } catch (e) {
      debugPrint('WinMonitor: detection error: $e');
      return null;
    }
  }
}

class _SimulatedApp {
  final String exe;
  final String title;
  final int pid;
  _SimulatedApp(this.exe, this.title, this.pid);
}
