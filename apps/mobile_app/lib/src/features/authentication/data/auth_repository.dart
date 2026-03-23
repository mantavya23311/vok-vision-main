import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AuthRepository {
  final Dio _dio;
  
  // For local testing on Android Emulator, use http://10.0.2.2:3000
  // For physical devices on the same network, use your machine's local IP
  static const String _baseUrl = 'http://192.168.200.84:3000/api/v1/auth';

  AuthRepository(this._dio);

  Future<void> requestOtp(String phoneNumber) async {
    try {
      final formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : '+91$phoneNumber';
      await _dio.post(
        '$_baseUrl/otp/request',
        data: {'phoneNumber': formattedPhone},
      );
    } on DioException catch (e) {
      final message = e.response?.data['message'] ?? 'Failed to request OTP';
      throw Exception(message);    
    }
  }

  Future<String> verifyOtp(String phoneNumber, String code) async {
    try {
      final formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : '+91$phoneNumber';
      final response = await _dio.post(
        '$_baseUrl/otp/verify',
        data: {
          'phoneNumber': formattedPhone,
          'code': code,
        },
      );
      
      return response.data['token'];
    } on DioException catch (e) {
      final message = e.response?.data['message'] ?? 'Failed to verify OTP';
      throw Exception(message);
    }
  }
}

final dioProvider = Provider<Dio>((ref) => Dio());

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(dioProvider));
});
