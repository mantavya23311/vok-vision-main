import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../shared/theme/responsive_layout.dart';
import 'create_project_overlay.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: context.widthPct(10)),
          child: Column(
            children: [
              const Spacer(flex: 3),
              
              // 1. Centered Minimal Empty State
              Center(
                child: Column(
                  children: [
                    // A very clean, subtle "+" button
                    GestureDetector(
                      onTap: () {
                        // Action to create new project
                      },
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: const Color(0xFF03081B).withOpacity(0.1),
                            width: 1.5,
                          ),
                        ),
                        child: const Icon(
                          Icons.add_rounded,
                          size: 32,
                          color: Color(0xFF03081B),
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                    Text(
                      'NO PROJECTS YET',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 3.0,
                        color: const Color(0xFF03081B).withOpacity(0.3),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Start your first 3D conversion\nby tapping the icon above.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        height: 1.6,
                        color: const Color(0xFF03081B).withOpacity(0.5),
                      ),
                    ),
                  ],
                ),
              ),
              
              const Spacer(flex: 4),

              // 2. Minimal Create Project Button at the bottom
              SizedBox(
                width: double.infinity,
                height: 54,
                child: OutlinedButton(
                  onPressed: () {
                    showModalBottomSheet(
                      context: context,
                      isScrollControlled: true,
                      backgroundColor: Colors.transparent,
                      builder: (context) => const CreateProjectOverlay(),
                    );
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF03081B), width: 1.2),
                    shape: const StadiumBorder(),
                  ),
                  child: Text(
                    'CREATE NEW',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      color: const Color(0xFF03081B),
                    ),
                  ),
                ),
              ),
              
              const SizedBox(height: 24),

              // 3. Subtle Brand Signature
              Text(
                'VOKVISION STUDIO',
                style: const TextStyle(
                  fontFamily: 'Monument',
                  fontSize: 10,
                  fontWeight: FontWeight.w400,
                  letterSpacing: 4.0,
                  color: Color(0xFFE5E5E5),
                ),
              ),
              
              SizedBox(height: context.heightPct(4)),
            ],
          ),
        ),
      ),
    );
  }
}
