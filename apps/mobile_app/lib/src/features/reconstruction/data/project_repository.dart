import 'dart:io';
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'package:camera/camera.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';
import '../../authentication/data/auth_repository.dart';

class ProjectRepository {
  final Dio _dio;
  
  // NOTE: Target your laptop's local IP address here
  static const String _baseUrl = 'http://192.168.200.84:3000/api/v1/projects';

  ProjectRepository(this._dio);

  Future<String> createProject({
    required String name,
    required String description,
    required String ownerPhone,
    String? fcmToken,
  }) async {
    try {
      final response = await _dio.post(
        _baseUrl,
        data: {
          'name': name,
          'description': description,
          'ownerPhone': ownerPhone,
          'fcmToken': fcmToken,
        },
      );
      return response.data['_id'];
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'Failed to create project');
    }
  }

  Future<File> _compressImage(XFile image) async {
    final bytes = await image.readAsBytes();
    final decodedImage = img.decodeImage(bytes);
    if (decodedImage == null) return File(image.path);

    // Resize to 1024x768 (Pro optimization)
    final resized = img.copyResize(decodedImage, width: 1024);
    
    final tempDir = await getTemporaryDirectory();
    final fileName = 'compressed_${p.basenameWithoutExtension(image.path)}.jpg';
    final compressedPath = p.join(tempDir.path, fileName);
    final compressedFile = File(compressedPath);
    await compressedFile.writeAsBytes(img.encodeJpg(resized, quality: 85));
    
    return compressedFile;
  }

  Future<void> uploadPhotos(String projectId, List<XFile> images) async {
    try {
      final formData = FormData();
      
      for (var image in images) {
        final compressedFile = await _compressImage(image);
        formData.files.add(MapEntry(
          'images',
          await MultipartFile.fromFile(
            compressedFile.path,
            filename: '${p.basenameWithoutExtension(image.path)}.jpg',
            contentType: MediaType('image', 'jpeg'),
          ),
        ));
      }

      await _dio.post(
        '$_baseUrl/$projectId/upload',
        data: formData,
        onSendProgress: (count, total) {
          if (total > 0) {
            print('Upload progress: ${(count / total * 100).toStringAsFixed(2)}%');
          }
        },
      );
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'Failed to upload photos');
    }
  }
}

final projectRepositoryProvider = Provider<ProjectRepository>((ref) {
  return ProjectRepository(ref.watch(dioProvider));
});
