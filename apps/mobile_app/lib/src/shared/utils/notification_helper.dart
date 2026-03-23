import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class NotificationHelper {
  static void showModernNotification({
    required BuildContext context,
    required String message,
    bool isError = false,
  }) {
    final scaffoldMessenger = ScaffoldMessenger.of(context);
    
    // Remove any existing snackbars to avoid stacking
    scaffoldMessenger.removeCurrentSnackBar();

    scaffoldMessenger.showSnackBar(
      SnackBar(
        content: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: isError ? const Color(0xFFFEE2E2) : const Color(0xFFECFDF5),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isError ? const Color(0xFFFECACA) : const Color(0xFFD1FAE5),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Icon(
                isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
                color: isError ? const Color(0xFFB91C1C) : const Color(0xFF047857),
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  message,
                  style: GoogleFonts.inter(
                    color: isError ? const Color(0xFF991B1B) : const Color(0xFF065F46),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.only(
          bottom: 40, // Consistent bottom margin for better visibility
          left: 20,
          right: 20,
        ),
        duration: const Duration(seconds: 3),
      ),
    );
  }
}
