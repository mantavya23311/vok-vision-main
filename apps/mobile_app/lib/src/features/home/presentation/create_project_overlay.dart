import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/theme/responsive_layout.dart';

class CreateProjectOverlay extends ConsumerStatefulWidget {
  const CreateProjectOverlay({super.key});

  @override
  ConsumerState<CreateProjectOverlay> createState() => _CreateProjectOverlayState();
}

class _CreateProjectOverlayState extends ConsumerState<CreateProjectOverlay> {
  final _nameController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        context.widthPct(8),
        32,
        context.widthPct(8),
        MediaQuery.of(context).viewInsets.bottom + 48,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'NEW PROJECT',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 3.0,
                  color: const Color(0xFF03081B).withOpacity(0.3),
                ),
              ),
              IconButton(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded, size: 20),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            'What are you scanning?',
            style: const TextStyle(
              fontFamily: 'Monument',
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Color(0xFF03081B),
            ),
          ),
          const SizedBox(height: 32),
          TextField(
            controller: _nameController,
            autofocus: true,
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: const Color(0xFF03081B),
            ),
            decoration: InputDecoration(
              hintText: 'e.g. Vintage Camera, Engine Part',
              hintStyle: GoogleFonts.inter(
                color: const Color(0xFF03081B).withOpacity(0.2),
              ),
              enabledBorder: const UnderlineInputBorder(
                borderSide: BorderSide(color: Color(0xFFEEEEEE)),
              ),
              focusedBorder: const UnderlineInputBorder(
                borderSide: BorderSide(color: Color(0xFF03081B)),
              ),
            ),
          ),
          const SizedBox(height: 48),
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: () {
                if (_nameController.text.isNotEmpty) {
                  final name = _nameController.text;
                  Navigator.pop(context);
                  context.push('/capture', extra: name);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF03081B),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
              ),
              child: Text(
                'START CAPTURE',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
