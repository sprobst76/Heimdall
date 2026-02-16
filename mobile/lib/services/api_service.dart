import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000/api/v1'; // Android emulator -> localhost

  final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiService() : _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
    headers: {'Content-Type': 'application/json'},
  )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry the original request
            final token = await _storage.read(key: 'access_token');
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(error.requestOptions);
            return handler.resolve(response);
          }
        }
        return handler.next(error);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await Dio(BaseOptions(baseUrl: baseUrl)).post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );

      await _storage.write(key: 'access_token', value: response.data['access_token']);
      await _storage.write(key: 'refresh_token', value: response.data['refresh_token']);
      return true;
    } catch (_) {
      await logout();
      return false;
    }
  }

  // Auth
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    final data = response.data;
    await _storage.write(key: 'access_token', value: data['access_token']);
    await _storage.write(key: 'refresh_token', value: data['refresh_token']);
    return data;
  }

  Future<Map<String, dynamic>> loginWithPin(String childName, String familyName, String pin) async {
    final response = await _dio.post('/auth/login-pin', data: {
      'child_name': childName,
      'family_name': familyName,
      'pin': pin,
    });
    final data = response.data;
    await _storage.write(key: 'access_token', value: data['access_token']);
    await _storage.write(key: 'refresh_token', value: data['refresh_token']);
    return data;
  }

  Future<Map<String, dynamic>> getMe() async {
    final response = await _dio.get('/auth/me');
    return response.data;
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }

  // Quests
  Future<List<dynamic>> getQuests(String childId, {String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final response = await _dio.get('/children/$childId/quests', queryParameters: params);
    return response.data;
  }

  Future<Map<String, dynamic>> claimQuest(String childId, String instanceId) async {
    final response = await _dio.post('/children/$childId/quests/$instanceId/claim');
    return response.data;
  }

  Future<Map<String, dynamic>> submitProof(String childId, String instanceId, String proofType, String proofUrl) async {
    final response = await _dio.post('/children/$childId/quests/$instanceId/proof', data: {
      'proof_type': proofType,
      'proof_url': proofUrl,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getQuestStats(String childId) async {
    final response = await _dio.get('/children/$childId/quests/stats');
    return response.data;
  }

  // File upload
  Future<Map<String, dynamic>> uploadProof(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
    });
    final response = await _dio.post('/uploads/proof', data: formData);
    return response.data;
  }

  // TANs
  Future<List<dynamic>> getTans(String childId, {String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final response = await _dio.get('/children/$childId/tans', queryParameters: params);
    return response.data;
  }

  Future<Map<String, dynamic>> redeemTan(String childId, String code) async {
    final response = await _dio.post('/children/$childId/tans/redeem', data: {'code': code});
    return response.data;
  }

  // Quest Templates (for display in child app)
  Future<List<dynamic>> getQuestTemplates(String familyId) async {
    final response = await _dio.get('/families/$familyId/quests');
    return response.data;
  }

  // Chat (LLM)
  Future<String> chat(String message, List<Map<String, String>> history) async {
    final response = await _dio.post('/llm/chat', data: {
      'message': message,
      'history': history,
    });
    return response.data['response'] as String;
  }

  Dio get dio => _dio;
}
