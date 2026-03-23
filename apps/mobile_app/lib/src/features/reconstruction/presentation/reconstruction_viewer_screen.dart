import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/theme/responsive_layout.dart';

class ReconstructionViewerScreen extends StatelessWidget {
  final String projectId;
  final String projectName;

  const ReconstructionViewerScreen({
    super.key,
    required this.projectId,
    required this.projectName,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. 3D Viewer Placeholder
          // In a production app, we would use a native metal/webgl viewer here.
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.view_in_ar_rounded,
                  color: Colors.white24,
                  size: 80,
                ),
                const SizedBox(height: 24),
                Text(
                  '3D MODEL VIEWER',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2.0,
                    color: Colors.white38,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Loading $projectName...',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: Colors.white10,
                  ),
                ),
              ],
            ),
          ),

          // 2. Header UI
          Positioned(
            top: 60,
            left: 24,
            right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                GestureDetector(
                  onTap: () => context.pop(),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
                  ),
                ),
                Column(
                  children: [
                    Text(
                      projectName.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: 'Monument',
                        fontSize: 14,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      'GAUSSIAN SPLAT',
                      style: GoogleFonts.inter(
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.0,
                        color: Colors.white.withOpacity(0.3),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 44), // Symmetry
              ],
            ),
          ),

          // 3. Bottom Controls
          Positioned(
            bottom: 40,
            left: 24,
            right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildActionButton(Icons.file_download_outlined, 'EXPORT'),
                _buildActionButton(Icons.share_outlined, 'SHARE'),
                _buildActionButton(Icons.delete_outline_rounded, 'DELETE', color: Colors.redAccent),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(IconData icon, String label, {Color color = Colors.white}) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: color.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withOpacity(0.1)),
          ),
          child: Icon(icon, color: color, size: 24),
        ),
        const SizedBox(height: 12),
        Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.0,
            color: color.withOpacity(0.5),
          ),
        ),
      ],
    );
  }
}
