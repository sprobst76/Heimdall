import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'services/api_service.dart';
import 'services/mock_api_service.dart';
import 'services/agent_bridge.dart';
import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/permission_setup_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize native agent bridge on Android
  if (defaultTargetPlatform == TargetPlatform.android) {
    AgentBridge.initialize();
  }

  runApp(const HeimdallRoot());
}

/// Root-Widget das bei Demo-Modus-Wechsel die gesamte App neu aufbaut.
class HeimdallRoot extends StatefulWidget {
  const HeimdallRoot({super.key});

  static _HeimdallRootState? _instance;

  /// Aktiviert den Demo-Modus und baut die App komplett neu auf.
  static void startDemoMode() {
    _instance?._enableDemoMode();
  }

  @override
  State<HeimdallRoot> createState() => _HeimdallRootState();
}

class _HeimdallRootState extends State<HeimdallRoot> {
  bool _emulatorMode = false;
  bool _autoLogin = false;
  int _rebuildKey = 0;

  @override
  void initState() {
    super.initState();
    HeimdallRoot._instance = this;
  }

  void _enableDemoMode() {
    setState(() {
      _emulatorMode = true;
      _autoLogin = true;
      _rebuildKey++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return HeimdallChildApp(
      key: ValueKey(_rebuildKey),
      emulatorMode: _emulatorMode,
      autoLogin: _autoLogin,
      onAutoLoginDone: () => _autoLogin = false,
    );
  }
}

class HeimdallChildApp extends StatelessWidget {
  final bool emulatorMode;
  final bool autoLogin;
  final VoidCallback? onAutoLoginDone;

  const HeimdallChildApp({
    super.key,
    this.emulatorMode = false,
    this.autoLogin = false,
    this.onAutoLoginDone,
  });

  @override
  Widget build(BuildContext context) {
    final apiService = emulatorMode ? MockApiService() : ApiService();

    return MultiProvider(
      providers: [
        Provider<ApiService>.value(value: apiService),
        ChangeNotifierProvider(create: (_) => AuthProvider(apiService)),
      ],
      child: MaterialApp(
        title: 'Heimdall',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF4F46E5),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          fontFamily: 'Roboto',
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF4F46E5),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        home: AuthGate(
          autoLogin: autoLogin,
          onAutoLoginDone: onAutoLoginDone,
        ),
      ),
    );
  }
}

class AuthGate extends StatefulWidget {
  final bool autoLogin;
  final VoidCallback? onAutoLoginDone;

  const AuthGate({
    super.key,
    this.autoLogin = false,
    this.onAutoLoginDone,
  });

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _permissionsOk = false;
  bool _permissionsChecked = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (widget.autoLogin) {
        widget.onAutoLoginDone?.call();
        final auth = context.read<AuthProvider>();
        await auth.login('demo@heimdall.de', 'demo');
      } else {
        context.read<AuthProvider>().checkAuth();
      }
    });
  }

  /// Prüft Berechtigungen und zeigt ggf. den Wizard an.
  Future<void> _checkAndSetupPermissions() async {
    if (_permissionsChecked) return;
    _permissionsChecked = true;

    if (defaultTargetPlatform != TargetPlatform.android) {
      setState(() => _permissionsOk = true);
      return;
    }

    try {
      final perms = await AgentBridge.checkPermissions();
      final hasAccessibility = perms['accessibility'] ?? false;
      final hasOverlay = perms['overlay'] ?? false;

      if (hasAccessibility && hasOverlay) {
        // Kritische Berechtigungen vorhanden → direkt weiter
        await AgentBridge.startMonitoring();
        if (widget.autoLogin) await _setupDemoBlocking();
        if (mounted) setState(() => _permissionsOk = true);
      } else {
        // Wizard anzeigen
        if (!mounted) return;
        final result = await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => const PermissionSetupScreen(),
          ),
        );
        if (result == true && widget.autoLogin) {
          await _setupDemoBlocking();
        }
        if (mounted) setState(() => _permissionsOk = true);
      }
    } catch (e) {
      debugPrint('Permission check error: $e');
      if (mounted) setState(() => _permissionsOk = true);
    }
  }

  Future<void> _setupDemoBlocking() async {
    try {
      await AgentBridge.updateAppGroupMap({
        'com.google.android.youtube': 'streaming',
        'com.google.android.apps.youtube.music': 'streaming',
        'com.instagram.android': 'social',
        'com.instagram.barcelona': 'social',
        'com.whatsapp': 'social',
        'com.android.chrome': 'browser',
        'com.google.android.apps.photos': 'fotos',
      });
      await AgentBridge.blockGroup('streaming');
      await AgentBridge.blockGroup('social');
    } catch (e) {
      debugPrint('Demo blocking setup error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isLoggedIn) {
          if (!_permissionsOk) {
            // Trigger permission check (einmalig nach Login)
            _checkAndSetupPermissions();
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          return const HomeScreen();
        }
        // Reset wenn ausgeloggt
        _permissionsOk = false;
        _permissionsChecked = false;
        return const LoginScreen();
      },
    );
  }
}
