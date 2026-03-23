import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Simple implementation for persistence
// In a full app, this would be in a repository
class OnboardingNotifier extends Notifier<bool> {
  @override
  bool build() => false;
  
  void complete() => state = true;
}

final onboardingCompleteProvider = NotifierProvider<OnboardingNotifier, bool>(OnboardingNotifier.new);

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError();
});
