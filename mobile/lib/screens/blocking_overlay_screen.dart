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
