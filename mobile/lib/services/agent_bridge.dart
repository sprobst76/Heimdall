import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'agent_bridge_windows.dart';

/// Platform-abstracted agent bridge.
///
/// On Android, communicates with the Kotlin agent via [MethodChannel].
/// On Windows, delegates to [WindowsAgentBridge] which runs the agent
/// directly in Dart (no separate process needed).
/// On other platforms (iOS, web, Linux), all methods are no-ops.
class AgentBridge {
  // Callbacks from native / agent
  static Function(String packageName)? onAppChanged;
  static Function(String packageName, String groupId)? onBlockTriggered;
  /// Fired when a group is approaching its daily limit (≤5 min remaining).
  static Function(String groupId, int remainingMinutes)? onLimitWarning;
  /// Fired when the monitoring service detects it was previously force-killed.
  static Function(String reason)? onTamperDetected;
  /// Fired when an active VPN or proxy is detected.
  static Function(String reason)? onVpnDetected;

  // -- Android MethodChannel --
  static const _channel = MethodChannel('de.heimdall/agent');

  // -- Windows Agent --
  static WindowsAgentBridge? _windowsBridge;

  static void initialize() {
    if (defaultTargetPlatform == TargetPlatform.android) {
      _channel.setMethodCallHandler(_handleMethod);
    } else if (Platform.isWindows) {
      _windowsBridge = WindowsAgentBridge();
      _windowsBridge!.onAppChanged = (pkg) => onAppChanged?.call(pkg);
      _windowsBridge!.onBlockTriggered = (pkg, gid) =>
          onBlockTriggered?.call(pkg, gid);
    }
  }

  static Future<dynamic> _handleMethod(MethodCall call) async {
    switch (call.method) {
      case 'onAppChanged':
        final pkg = call.arguments['packageName'] as String;
        onAppChanged?.call(pkg);
        break;
      case 'onBlockTriggered':
        final pkg = call.arguments['packageName'] as String;
        final groupId = call.arguments['groupId'] as String;
        onBlockTriggered?.call(pkg, groupId);
        break;
      case 'onLimitWarning':
        final groupId = call.arguments['groupId'] as String;
        final remaining = call.arguments['remainingMinutes'] as int;
        onLimitWarning?.call(groupId, remaining);
        break;
      case 'onTamperDetected':
        final reason = call.arguments['reason'] as String? ?? 'unknown';
        onTamperDetected?.call(reason);
        break;
      case 'onVpnDetected':
        final reason = call.arguments['reason'] as String? ?? 'unknown';
        onVpnDetected?.call(reason);
        break;
    }
  }

  // -- Monitoring control --

  static Future<bool> startMonitoring() async {
    if (_windowsBridge != null) return _windowsBridge!.startMonitoring();
    return await _channel.invokeMethod<bool>('startMonitoring') ?? false;
  }

  static Future<bool> stopMonitoring() async {
    if (_windowsBridge != null) return _windowsBridge!.stopMonitoring();
    return await _channel.invokeMethod<bool>('stopMonitoring') ?? false;
  }

  static Future<bool> isMonitoringActive() async {
    if (_windowsBridge != null) return _windowsBridge!.isMonitoringActive();
    return await _channel.invokeMethod<bool>('isMonitoringActive') ?? false;
  }

  // -- Permissions --

  static Future<Map<String, bool>> checkPermissions() async {
    if (_windowsBridge != null) return _windowsBridge!.checkPermissions();
    final result = await _channel.invokeMethod<Map>('checkPermissions');
    if (result == null) return {};
    return result.map((key, value) => MapEntry(key.toString(), value as bool));
  }

  static Future<void> requestAccessibility() async {
    if (_windowsBridge != null) return _windowsBridge!.requestAutostart();
    await _channel.invokeMethod('requestAccessibility');
  }

  static Future<void> requestUsageStats() async {
    if (_windowsBridge != null) return; // not needed on Windows
    await _channel.invokeMethod('requestUsageStats');
  }

  static Future<void> requestDeviceAdmin() async {
    if (_windowsBridge != null) return; // not needed on Windows
    await _channel.invokeMethod('requestDeviceAdmin');
  }

  static Future<void> requestOverlay() async {
    if (_windowsBridge != null) return; // not needed on Windows (Flutter handles it)
    await _channel.invokeMethod('requestOverlay');
  }

  // -- Configuration --

  static Future<void> configure({
    required String serverUrl,
    required String deviceToken,
    required String deviceId,
  }) async {
    if (_windowsBridge != null) return; // TODO: implement for Windows
    await _channel.invokeMethod('configure', {
      'serverUrl': serverUrl,
      'deviceToken': deviceToken,
      'deviceId': deviceId,
    });
  }

  // -- Data --

  static Future<Map<String, int>> getUsageToday() async {
    if (_windowsBridge != null) return _windowsBridge!.getUsageToday();
    final result = await _channel.invokeMethod<Map>('getUsageToday');
    if (result == null) return {};
    return result.map((key, value) => MapEntry(key.toString(), value as int));
  }

  static Future<String?> fetchRules() async {
    if (_windowsBridge != null) return null; // demo mode uses local rules
    return await _channel.invokeMethod<String>('fetchRules');
  }

  static Future<void> sendHeartbeat() async {
    if (_windowsBridge != null) return; // no backend in demo mode
    await _channel.invokeMethod('sendHeartbeat');
  }

  static Future<void> blockGroup(String groupId) async {
    if (_windowsBridge != null) return _windowsBridge!.blockGroup(groupId);
    await _channel.invokeMethod('blockGroup', {'groupId': groupId});
  }

  static Future<void> unblockGroup(String groupId) async {
    if (_windowsBridge != null) return _windowsBridge!.unblockGroup(groupId);
    await _channel.invokeMethod('unblockGroup', {'groupId': groupId});
  }

  static Future<void> updateAppGroupMap(Map<String, String> map) async {
    if (_windowsBridge != null) return; // uses kDemoAppGroupMap
    await _channel.invokeMethod('updateAppGroupMap', {'map': map});
  }

  // -- Blocking overlay --

  static Future<void> showBlockOverlay(String packageName, String groupId) async {
    if (_windowsBridge != null) return; // handled via onBlockTriggered callback
    await _channel.invokeMethod('showBlockOverlay', {
      'packageName': packageName,
      'groupId': groupId,
    });
  }

  static Future<void> hideBlockOverlay() async {
    if (_windowsBridge != null) return;
    await _channel.invokeMethod('hideBlockOverlay');
  }

  // -- Windows-specific access --

  /// Get the Windows agent bridge (null on other platforms).
  static WindowsAgentBridge? get windowsBridge => _windowsBridge;
}
