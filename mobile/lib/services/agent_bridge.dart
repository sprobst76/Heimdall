import 'dart:async';
import 'package:flutter/services.dart';

class AgentBridge {
  static const _channel = MethodChannel('de.heimdall/agent');

  // Callbacks from native
  static Function(String packageName)? onAppChanged;
  static Function(String packageName, String groupId)? onBlockTriggered;

  static void initialize() {
    _channel.setMethodCallHandler(_handleMethod);
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
    }
  }

  // -- Monitoring control --

  static Future<bool> startMonitoring() async {
    return await _channel.invokeMethod<bool>('startMonitoring') ?? false;
  }

  static Future<bool> stopMonitoring() async {
    return await _channel.invokeMethod<bool>('stopMonitoring') ?? false;
  }

  static Future<bool> isMonitoringActive() async {
    return await _channel.invokeMethod<bool>('isMonitoringActive') ?? false;
  }

  // -- Permissions --

  static Future<Map<String, bool>> checkPermissions() async {
    final result = await _channel.invokeMethod<Map>('checkPermissions');
    if (result == null) return {};
    return result.map((key, value) => MapEntry(key.toString(), value as bool));
  }

  static Future<void> requestAccessibility() async {
    await _channel.invokeMethod('requestAccessibility');
  }

  static Future<void> requestUsageStats() async {
    await _channel.invokeMethod('requestUsageStats');
  }

  static Future<void> requestDeviceAdmin() async {
    await _channel.invokeMethod('requestDeviceAdmin');
  }

  static Future<void> requestOverlay() async {
    await _channel.invokeMethod('requestOverlay');
  }

  // -- Configuration --

  static Future<void> configure({
    required String serverUrl,
    required String deviceToken,
    required String deviceId,
  }) async {
    await _channel.invokeMethod('configure', {
      'serverUrl': serverUrl,
      'deviceToken': deviceToken,
      'deviceId': deviceId,
    });
  }

  // -- Data --

  static Future<Map<String, int>> getUsageToday() async {
    final result = await _channel.invokeMethod<Map>('getUsageToday');
    if (result == null) return {};
    return result.map((key, value) => MapEntry(key.toString(), value as int));
  }

  static Future<String?> fetchRules() async {
    return await _channel.invokeMethod<String>('fetchRules');
  }

  static Future<void> sendHeartbeat() async {
    await _channel.invokeMethod('sendHeartbeat');
  }

  static Future<void> blockGroup(String groupId) async {
    await _channel.invokeMethod('blockGroup', {'groupId': groupId});
  }

  static Future<void> unblockGroup(String groupId) async {
    await _channel.invokeMethod('unblockGroup', {'groupId': groupId});
  }

  static Future<void> updateAppGroupMap(Map<String, String> map) async {
    await _channel.invokeMethod('updateAppGroupMap', {'map': map});
  }

  // -- Blocking overlay --

  static Future<void> showBlockOverlay(String packageName, String groupId) async {
    await _channel.invokeMethod('showBlockOverlay', {
      'packageName': packageName,
      'groupId': groupId,
    });
  }

  static Future<void> hideBlockOverlay() async {
    await _channel.invokeMethod('hideBlockOverlay');
  }
}
