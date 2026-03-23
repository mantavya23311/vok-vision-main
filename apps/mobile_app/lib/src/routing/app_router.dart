import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/onboarding/presentation/splash_screen.dart';
import '../features/onboarding/presentation/onboarding_screen.dart';
import '../features/authentication/presentation/auth_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/capture/presentation/capture_screen.dart';
import '../features/reconstruction/presentation/reconstruction_viewer_screen.dart';
import '../features/reconstruction/presentation/processing_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    debugLogDiagnostics: true,
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        pageBuilder: (context, state) => CustomTransitionPage(
          key: state.pageKey,
          child: const OnboardingScreen(),
          transitionDuration: const Duration(milliseconds: 600),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return FadeTransition(
              opacity: CurveTween(curve: Curves.easeInOut).animate(animation),
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.1),
                  end: Offset.zero,
                ).animate(
                  CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeInOut,
                  ),
                ),
                child: child,
              ),
            );
          },
        ),
      ),
      GoRoute(
        path: '/auth',
        builder: (context, state) => const AuthScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/capture',
        pageBuilder: (context, state) {
          final projectName = state.extra as String? ?? 'New Project';
          return CustomTransitionPage(
            key: state.pageKey,
            child: CaptureScreen(projectName: projectName),
            transitionDuration: const Duration(milliseconds: 600),
            transitionsBuilder: (context, animation, secondaryAnimation, child) {
              return SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 1),
                  end: Offset.zero,
                ).animate(
                  CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeOutCubic,
                  ),
                ),
                child: child,
              );
            },
          );
        },
      ),
      GoRoute(
        path: '/viewer/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          final name = state.uri.queryParameters['name'] ?? '3D Project';
          return ReconstructionViewerScreen(
            projectId: id,
            projectName: name,
          );
        },
      ),
      GoRoute(
        path: '/processing/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          final name = state.extra as String? ?? 'Processing Project';
          return ProcessingScreen(
            projectId: id,
            projectName: name,
          );
        },
      ),
    ],
  );
});
