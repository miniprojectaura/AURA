/// Centralized environment config for the app.
///
/// Change [apiBaseUrl] for production vs development builds.
class Env {
  Env._();

  /// Backend API base URL.
  ///
  /// Production: https://aura1-3rk2.onrender.com
  /// Local dev:  http://10.0.2.2:8000  (Android emulator → localhost)
  static const String apiBaseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://aura1-3rk2.onrender.com',
  );

  /// WebSocket URL derived from [apiBaseUrl].
  static String get wsBaseUrl =>
      apiBaseUrl
          .replaceFirst('https://', 'wss://')
          .replaceFirst('http://', 'ws://');
}
