import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import '../data/reconstruction_provider.dart';
import '../domain/reconstruction_progress.dart';

class ProcessingScreen extends ConsumerWidget {
  final String projectId;
  final String projectName;

  const ProcessingScreen({
    super.key,
    required this.projectId,
    required this.projectName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressAsync = ref.watch(reconstructionProgressProvider(projectId));
    final progress = progressAsync.value ?? ReconstructionProgress.initial();

    // Switch to viewer when finished
    if (progress.stage == ReconstructionStage.completed) {
      Future.delayed(Duration.zero, () {
        context.pushReplacement('/viewer/$projectId', extra: projectName);
      });
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. Dynamic Background Glows
          _buildBackgroundGlow(),

          // 2. Main Content
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 40),
                  
                  // Header
                  Text(
                    'RECONSTRUCTING',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 4.0,
                      color: Colors.white.withOpacity(0.5),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    projectName,
                    style: const TextStyle(
                      fontFamily: 'Monument',
                      fontSize: 24,
                      color: Colors.white,
                    ),
                  ),
                  
                  const SizedBox(height: 60),

                  // Central Visualization
                  _buildCentralVisual(progress),

                  const SizedBox(height: 60),

                  // Stage Steps
                  _buildProgressTimeline(progress),

                  const Spacer(),

                  // Tip/Status
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: Colors.white.withOpacity(0.1)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.lightbulb_outline_rounded, color: Colors.amberAccent, size: 20),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Text(
                            'AI is currently ${progress.message.toLowerCase()}. This usually takes 10-12 minutes on M1.',
                            style: GoogleFonts.inter(
                              color: Colors.white70,
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCentralVisual(ReconstructionProgress progress) {
    return Stack(
      alignment: Alignment.center,
      children: [
        // Pulsing Ring
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.0, end: 1.0),
          duration: const Duration(seconds: 2),
          builder: (context, value, child) {
            return Container(
              width: 200 + (20 * value),
              height: 200 + (20 * value),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.blueAccent.withOpacity(0.2 * (1 - value)),
                  width: 2,
                ),
              ),
            );
          },
        ),
        
        // Progress Circle
        SizedBox(
          width: 180,
          height: 180,
          child: CircularProgressIndicator(
            value: progress.progress,
            strokeWidth: 4,
            backgroundColor: Colors.white.withOpacity(0.05),
            color: Colors.blueAccent,
          ),
        ),

        // 3D Icon or Percent
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.blur_on_rounded, color: Colors.white, size: 48),
            const SizedBox(height: 8),
            Text(
              '${(progress.progress * 100).toInt()}%',
              style: GoogleFonts.inter(
                fontSize: 32,
                fontWeight: FontWeight.w800,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildProgressTimeline(ReconstructionProgress progress) {
    return Column(
      children: [
        _buildStep(
          'AUDITING', 
          'Quality check via Gemini', 
          progress.stage.index >= ReconstructionStage.auditing.index,
          progress.stage == ReconstructionStage.auditing,
        ),
        _buildStep(
          'MAPPING', 
          'Pose estimation (MASt3R)', 
          progress.stage.index >= ReconstructionStage.mapping.index,
          progress.stage == ReconstructionStage.mapping,
        ),
        _buildStep(
          'TRAINING', 
          'Gaussian Painting (OpenSplat)', 
          progress.stage.index >= ReconstructionStage.training.index,
          progress.stage == ReconstructionStage.training,
        ),
      ],
    );
  }

  Widget _buildStep(String title, String sub, bool isDone, bool isCurrent) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12.0),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isDone ? Colors.blueAccent : (isCurrent ? Colors.blueAccent.withOpacity(0.2) : Colors.white10),
            ),
            child: isDone 
              ? const Icon(Icons.check, size: 14, color: Colors.white)
              : (isCurrent ? const Center(child: SizedBox(width: 10, height: 10, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.blueAccent))) : null),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    color: isDone || isCurrent ? Colors.white : Colors.white24,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                    fontSize: 13,
                  ),
                ),
                Text(
                  sub,
                  style: GoogleFonts.inter(
                    color: isDone || isCurrent ? Colors.white38 : Colors.white10,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          if (isCurrent)
            const Text(
              'IN PROGRESS',
              style: TextStyle(color: Colors.blueAccent, fontSize: 10, fontWeight: FontWeight.bold),
            ),
        ],
      ),
    );
  }

  Widget _buildBackgroundGlow() {
    return Stack(
      children: [
        Positioned(
          top: -100,
          right: -50,
          child: Container(
            width: 300,
            height: 300,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.blueAccent.withOpacity(0.15),
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 100, sigmaY: 100),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),
        Positioned(
          bottom: 100,
          left: -100,
          child: Container(
            width: 400,
            height: 400,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.purpleAccent.withOpacity(0.1),
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 120, sigmaY: 120),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),
      ],
    );
  }
}
