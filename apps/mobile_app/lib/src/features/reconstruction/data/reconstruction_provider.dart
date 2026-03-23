import 'dart:async';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/reconstruction_progress.dart';

final reconstructionProgressProvider = StreamProvider.family<ReconstructionProgress, String>((ref, projectId) {
  // Use a controller to bridge the global stream to this family provider
  final controller = StreamController<ReconstructionProgress>();
  
  // Emit initial state immediately
  controller.add(ReconstructionProgress.initial());

  final subscription = FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    final data = message.data;
    if ((data['type'] == 'PROGRESS_UPDATE' || data['type'] == 'PROJECT_COMPLETED') && 
        data['projectId'] == projectId) {
      controller.add(ReconstructionProgress.fromMap(data));
    }
  });

  ref.onDispose(() {
    subscription.cancel();
    controller.close();
  });

  return controller.stream;
});
