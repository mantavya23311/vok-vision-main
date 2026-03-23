import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'src/app.dart';
import 'package:flutter/foundation.dart';

void main() async {
  // Ensure Flutter bindings are initialized
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase (Safely for Web)
  try {
    if (kIsWeb) {
      // For web, you might need actual options, but this prevents the crash
      debugPrint('Running on Web - skipping native Firebase setup');
    } else {
      await Firebase.initializeApp();
      
      // Handle background messages (Only for native)
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

      // Handle foreground messages
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint('Foreground message received: ${message.notification?.title}');
      });
    }
  } catch (e) {
    debugPrint('Firebase init error: $e');
  }
  
  runApp(
    const ProviderScope(
      child: VokVisionApp(),
    ),
  );
}

// Background handler must be a top-level function
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  debugPrint('Background message received: ${message.notification?.title}');
}
