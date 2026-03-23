import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../../../shared/theme/responsive_layout.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<OnboardingData> _pages = [
    OnboardingData(
      title: 'Unify',
      description: 'The 3D reconstruction tool you need.',
      imagePath: 'assests/onboard2.png',
    ),
    OnboardingData(
      title: 'Capture',
      description: 'Turn photos into detailed 3D models.',
      imagePath: 'assests/onboard2.png',
    ),
    OnboardingData(
      title: 'Perfect',
      description: 'Professional tools at your fingertips.',
      imagePath: 'assests/onboard2.png',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            SizedBox(height: context.heightPct(6)),
            // Content
            // Using AnimatedSwitcher for smooth cross-fade transition
            SizedBox(
              height: context.heightPct(22),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 100),
                transitionBuilder: (Widget child, Animation<double> animation) {
                  return FadeTransition(opacity: animation, child: child);
                },
                child: Column(
                  key: ValueKey<int>(_currentPage),
                  children: [
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: context.widthPct(4)),
                      child: Text(
                        _pages[_currentPage].title,
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontFamily: 'Monument',
                          fontSize: 40,
                          fontWeight: FontWeight.w600,
                          height: 1.0,
                          color: Color(0xFF03081B),
                        ),
                      ),
                    ),
                    SizedBox(height: context.heightPct(1)),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: context.widthPct(8)),
                      child: Text(
                        _pages[_currentPage].description,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          color: const Color(0xFF03081B).withOpacity(0.6),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // 3. Sliding Image Area (Full Width, No Padding)
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) => setState(() => _currentPage = index),
                itemCount: _pages.length,
                itemBuilder: (context, index) {
                  final data = _pages[index];
                  return Image.asset(
                    data.imagePath,
                    fit: BoxFit.contain, // Maintain aspect ratio but allow full width feel
                  );
                },
              ),
            ),

            // 4. Bottom Section (Indicator & Buttons)
            Padding(
              padding: EdgeInsets.only(
                bottom: context.heightPct(4),
                top: context.heightPct(2),
              ),
              child: Column(
                children: [
                  // Page Indicator
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(
                      _pages.length,
                      (index) => AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 8,
                        width: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _currentPage == index
                              ? const Color(0xFF03081B)
                              : const Color(0xFF03081B).withOpacity(0.2),
                        ),
                      ),
                    ),
                  ),
                  SizedBox(height: context.heightPct(4)),
                  
                  // Buttons
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: context.widthPct(4)),
                    child: Row(
                      children: [
                        // SIGN IN (Outlined Pill)
                        Expanded(
                          child: SizedBox(
                            height: 43,
                            child: OutlinedButton(
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(color: Color(0xFF03081B)),
                                shape: const StadiumBorder(),
                              ),
                              onPressed: () => context.push('/auth'),
                              child: Text(
                                'SIGN IN',
                                style: GoogleFonts.inter(
                                  color: const Color(0xFF03081B),
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 1.0,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        // SIGN UP (Filled Pill)
                        Expanded(
                          child: SizedBox(
                            height: 43,
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF03081B),
                                foregroundColor: Colors.white,
                                elevation: 0,
                                shape: const StadiumBorder(),
                              ),
                              onPressed: () => context.push('/auth'),
                              child: Text(
                                'SIGN UP',
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 1.0,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class OnboardingData {
  final String title;
  final String description;
  final String imagePath;

  OnboardingData({
    required this.title,
    required this.description,
    required this.imagePath,
  });
}
