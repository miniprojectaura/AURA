/// API Service — Dio-based HTTP client with JWT injection.
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/env.dart';

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

class ApiService {
  late final Dio _dio;
  String? _accessToken;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));

    // JWT interceptor
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Token expired — try refresh
          final refreshed = await _refreshToken();
          if (refreshed) {
            final retryOpts = error.requestOptions;
            retryOpts.headers['Authorization'] = 'Bearer $_accessToken';
            final response = await _dio.fetch(retryOpts);
            return handler.resolve(response);
          }
        }
        handler.next(error);
      },
    ));
  }

  // ── Auth ────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    final response = await _dio.post('/api/v1/auth/register', data: {
      'email': email,
      'password': password,
      'display_name': displayName,
    });
    _accessToken = response.data['access_token'];
    await _saveToken(response.data);
    return response.data;
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post('/api/v1/auth/login', data: {
      'email': email,
      'password': password,
    });
    _accessToken = response.data['access_token'];
    await _saveToken(response.data);
    return response.data;
  }

  // ── Chat ────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> createSession({String language = 'en'}) async {
    final response = await _dio.post('/api/v1/chat/sessions', data: {
      'language': language,
    });
    return response.data;
  }

  Future<List<dynamic>> listSessions() async {
    final response = await _dio.get('/api/v1/chat/sessions');
    return response.data;
  }

  Future<List<dynamic>> getMessages(String sessionId) async {
    final response = await _dio.get('/api/v1/chat/sessions/$sessionId/messages');
    return response.data;
  }

  String get wsUrl => '${Env.wsBaseUrl}/api/v1/chat/ws';
  String? get token => _accessToken;

  // ── Design ──────────────────────────────────────────────────────
  Future<Map<String, dynamic>> generateDesign({
    String? occasion,
    String? bodyType,
    List<String> colors = const [],
    List<String> styleKeywords = const [],
    List<String> garmentTypes = const [],
    String? culturalContext,
  }) async {
    final response = await _dio.post('/api/v1/design/generate', data: {
      'occasion': occasion,
      'body_type': bodyType,
      'colors': colors,
      'style_keywords': styleKeywords,
      'garment_types': garmentTypes,
      'cultural_context': culturalContext,
    });
    return response.data;
  }

  // ── Wardrobe ────────────────────────────────────────────────────
  Future<List<dynamic>> getWardrobeItems({String? category}) async {
    final queryParams = <String, dynamic>{};
    if (category != null) queryParams['category'] = category;
    final response = await _dio.get('/api/v1/wardrobe/', queryParameters: queryParams);
    return response.data;
  }

  Future<Map<String, dynamic>> addWardrobeItem({
    required String name,
    required String category,
    String? color,
    String? imageUrl,
    String? notes,
  }) async {
    final response = await _dio.post('/api/v1/wardrobe/', data: {
      'name': name,
      'category': category,
      'color': color,
      'image_url': imageUrl,
      'notes': notes,
    });
    return response.data;
  }

  Future<void> deleteWardrobeItem(String itemId) async {
    await _dio.delete('/api/v1/wardrobe/$itemId');
  }

  Future<Map<String, dynamic>> suggestOutfit({required String occasion}) async {
    final response = await _dio.post('/api/v1/wardrobe/suggest-outfit',
      queryParameters: {'occasion': occasion},
    );
    return response.data;
  }

  // ── Search ──────────────────────────────────────────────────────
  Future<List<dynamic>> searchProducts({
    required String query,
    int limit = 10,
  }) async {
    final response = await _dio.post('/api/v1/search/products', data: {
      'query': query,
      'limit': limit,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getTrending({String? category}) async {
    final queryParams = <String, dynamic>{};
    if (category != null) queryParams['category'] = category;
    final response = await _dio.get('/api/v1/search/trending', queryParameters: queryParams);
    return response.data;
  }

  // ── Profile ─────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getProfile() async {
    final response = await _dio.get('/api/v1/auth/me');
    return response.data;
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/auth/me', data: data);
    return response.data;
  }

  Future<void> logoutServer() async {
    await _dio.post('/api/v1/auth/logout');
  }

  // ── Token management ────────────────────────────────────────────
  Future<void> _saveToken(Map<String, dynamic> authData) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', authData['access_token'] ?? '');
    await prefs.setString('refresh_token', authData['refresh_token'] ?? '');
  }

  Future<void> loadSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString('access_token');
  }

  Future<bool> _refreshToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final refreshToken = prefs.getString('refresh_token');
      if (refreshToken == null) return false;

      final response = await _dio.post('/api/v1/auth/refresh', data: {
        'refresh_token': refreshToken,
      });
      _accessToken = response.data['access_token'];
      await _saveToken(response.data);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    _accessToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }
}
