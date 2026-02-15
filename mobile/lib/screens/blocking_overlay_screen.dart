import 'dart:async';
import 'package:flutter/material.dart';

/// Fullscreen blocking overlay — shown when a blocked app is detected.
///
/// On Android this is handled by the native BlockingOverlayService.
/// On Windows this is a Flutter widget shown in the main window
/// (set to fullscreen + always-on-top via window_manager).
class BlockingOverlayScreen extends StatelessWidget {
  final String appName;
  final String groupName;
  final int usedMinutes;
  final int limitMinutes;
  final VoidCallback? onDismiss;

  const BlockingOverlayScreen({
    super.key,
    required this.appName,
    required this.groupName,
    required this.usedMinutes,
    required this.limitMinutes,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1a1a2e),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Shield icon
                Container(
                  width: 96,
                  height: 96,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Colors.amber.shade600,
                        Colors.amber.shade900,
                      ],
                    ),
                  ),
                  child: const Icon(
                    Icons.shield,
                    size: 56,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 32),

                // Title
                Text(
                  'App gesperrt',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 16),

                // App name
                Text(
                  '"$appName" ist gerade nicht erlaubt.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: Colors.white70,
                      ),
                ),
                const SizedBox(height: 8),

                // Category
                Text(
                  'Kategorie: $groupName',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white54,
                      ),
                ),

                if (limitMinutes > 0 && limitMinutes < 999) ...[
                  const SizedBox(height: 4),
                  Text(
                    '$groupName-Zeit: $usedMinutes / $limitMinutes Minuten',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.white54,
                        ),
                  ),
                ],

                const SizedBox(height: 32),

                // Quest hint
                Text(
                  'Erledige Quests, um Bildschirmzeit\nfür diese Kategorie freizuschalten!',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.amber.shade300,
                      ),
                ),

                const SizedBox(height: 40),

                // Back button
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton(
                    onPressed: onDismiss,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF4F46E5),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(26),
                      ),
                    ),
                    child: const Text(
                      'Zurück zu Heimdall',
                      style: TextStyle(fontSize: 16),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Vollsperrung — fullscreen lockdown overlay with countdown.
///
/// Covers the entire screen (via window_manager fullscreen + always-on-top).
/// Shows a countdown timer and cannot be dismissed until time runs out.
class FullLockdownScreen extends StatefulWidget {
  final int durationSeconds;
  final VoidCallback? onFinished;

  const FullLockdownScreen({
    super.key,
    required this.durationSeconds,
    this.onFinished,
  });

  @override
  State<FullLockdownScreen> createState() => _FullLockdownScreenState();
}

class _FullLockdownScreenState extends State<FullLockdownScreen> {
  late int _remaining;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _remaining = widget.durationSeconds;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_remaining <= 1) {
        _timer?.cancel();
        widget.onFinished?.call();
      } else {
        setState(() => _remaining--);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String get _formattedTime {
    final min = _remaining ~/ 60;
    final sec = _remaining % 60;
    if (min > 0) return '$min:${sec.toString().padLeft(2, '0')}';
    return '${sec}s';
  }

  @override
  Widget build(BuildContext context) {
    final progress = _remaining / widget.durationSeconds;

    return Scaffold(
      backgroundColor: const Color(0xFF1a1a2e),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Lock icon with circular progress
              SizedBox(
                width: 120,
                height: 120,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 120,
                      height: 120,
                      child: CircularProgressIndicator(
                        value: progress,
                        strokeWidth: 6,
                        backgroundColor: Colors.white12,
                        valueColor: AlwaysStoppedAnimation(
                          Colors.red.shade400,
                        ),
                      ),
                    ),
                    Container(
                      width: 88,
                      height: 88,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Colors.red.shade600,
                            Colors.red.shade900,
                          ],
                        ),
                      ),
                      child: const Icon(
                        Icons.lock,
                        size: 48,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              // Title
              Text(
                'Bildschirm gesperrt',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 16),

              // Explanation
              Text(
                'Deine Bildschirmzeit für heute ist aufgebraucht.\n'
                'Der Computer wird gleich wieder freigegeben.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Colors.white70,
                    ),
              ),
              const SizedBox(height: 32),

              // Countdown
              Text(
                _formattedTime,
                style: Theme.of(context).textTheme.displayLarge?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontFeatures: [const FontFeature.tabularFigures()],
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                'verbleibend',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white54,
                    ),
              ),

              const SizedBox(height: 40),

              // Quest hint
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withAlpha(13),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.amber.withAlpha(51)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.emoji_events, color: Colors.amber.shade300),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Erledige Quests, um morgen mehr '
                        'Bildschirmzeit zu bekommen!',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.amber.shade300,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
