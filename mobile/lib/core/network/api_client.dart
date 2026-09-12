import "package:dio/dio.dart";

import "../../config/env.dart";
import "../storage/secure_storage.dart";

/// Thin wrapper around Dio: injects the bearer token when present and normalizes errors
/// into [ApiException] so presentation code has one error shape to render (loading / empty /
/// error / offline states per spec §79).
class ApiClient {
  ApiClient({SecureStorage? secureStorage, Dio? dio})
      : _secureStorage = secureStorage ?? SecureStorage(),
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: Env.apiBaseUrl,
              connectTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 15),
            )) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _secureStorage.accessToken;
          if (token != null) {
            options.headers["Authorization"] = "Bearer $token";
          }
          handler.next(options);
        },
        onError: (error, handler) => handler.next(error),
      ),
    );
  }

  final Dio _dio;
  final SecureStorage _secureStorage;

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters}) =>
      _wrap(() => _dio.get<T>(path, queryParameters: queryParameters));

  Future<Response<T>> post<T>(String path, {dynamic data}) =>
      _wrap(() => _dio.post<T>(path, data: data));

  Future<Response<T>> put<T>(String path, {dynamic data}) =>
      _wrap(() => _dio.put<T>(path, data: data));

  Future<Response<T>> delete<T>(String path) => _wrap(() => _dio.delete<T>(path));

  Future<Response<T>> _wrap<T>(Future<Response<T>> Function() request) async {
    try {
      return await request();
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    }
  }
}

enum ApiErrorKind { network, unauthorized, notFound, validation, server, unknown }

class ApiException implements Exception {
  ApiException(this.kind, this.message);

  final ApiErrorKind kind;
  final String message;

  factory ApiException.fromDioException(DioException e) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return ApiException(ApiErrorKind.network, "You appear to be offline.");
    }
    final status = e.response?.statusCode;
    final detail = e.response?.data is Map ? e.response?.data["detail"] as String? : null;
    return switch (status) {
      401 => ApiException(ApiErrorKind.unauthorized, detail ?? "Session expired. Please log in again."),
      404 => ApiException(ApiErrorKind.notFound, detail ?? "Not found."),
      422 => ApiException(ApiErrorKind.validation, detail ?? "Please check your input."),
      >= 500 => ApiException(ApiErrorKind.server, detail ?? "Something went wrong. Please try again."),
      _ => ApiException(ApiErrorKind.unknown, detail ?? "Something went wrong."),
    };
  }

  @override
  String toString() => message;
}
