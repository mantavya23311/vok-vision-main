import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:pinput/pinput.dart';
import 'package:smart_auth/smart_auth.dart';
import '../../../shared/theme/responsive_layout.dart';
import '../../../shared/utils/notification_helper.dart';

import '../data/auth_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  bool _isOtpSent = false;
  bool _isLoading = false;
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _otpController = TextEditingController();
  final SmartAuth _smartAuth = SmartAuth.instance;

  @override
  void initState() {
    super.initState();
    _getPhoneHint();
  }

  Future<void> _getPhoneHint() async {
    try {
      final res = await _smartAuth.requestPhoneNumberHint();
      if (res.hasData && res.data!.isNotEmpty) {
        String phone = res.data!;
        if (phone.startsWith('+91')) {
          phone = phone.substring(3);
        } else if (phone.startsWith('91')) {
          phone = phone.substring(2);
        }
        setState(() {
          _phoneController.text = phone;
        });
      }
    } catch (e) {
      debugPrint('Phone hint error: $e');
    }
  }

  Future<void> _listenForSms() async {
    try {
      final res = await _smartAuth.getSmsWithUserConsentApi();
      if (res.hasData && res.data != null && res.data!.code != null) {
        final code = res.data!.code!;
        if (_isLoading) return; // Guard against existing verification
        
        setState(() {
          _otpController.text = code;
        });
        // Pinput's onCompleted might trigger automatically when controller updates
        // but adding this call ensures it proceeds either way.
        _handleVerifyOtp(code);
      }
    } catch (e) {
      debugPrint('SMS listen error: $e');
    }
  }

  Future<void> _handleRequestOtp() async {
    if (_phoneController.text.length != 10) {
      NotificationHelper.showModernNotification(
        context: context,
        message: 'Please enter a valid 10-digit number',
        isError: true,
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ref.read(authRepositoryProvider).requestOtp(_phoneController.text);
      if (mounted) {
        NotificationHelper.showModernNotification(
          context: context,
          message: 'Verification code sent to your phone',
        );
      }
      setState(() => _isOtpSent = true);
      _listenForSms();
    } catch (e) {
      if (mounted) {
        NotificationHelper.showModernNotification(
          context: context,
          message: e.toString().contains('Exception:') ? e.toString().replaceAll('Exception: ', '') : e.toString(),
          isError: true,
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleVerifyOtp(String pin) async {
    if (pin.length != 6 || _isLoading) return;
    
    setState(() => _isLoading = true);
    try {
      await ref.read(authRepositoryProvider).verifyOtp(_phoneController.text, pin);
      if (mounted) {
        NotificationHelper.showModernNotification(
          context: context,
          message: 'Authentication successful. Welcome back',
        );
        context.push('/home');
      }
    } catch (e) {
      if (mounted) {
        NotificationHelper.showModernNotification(
          context: context,
          message: e.toString().contains('Exception:') ? e.toString().replaceAll('Exception: ', '') : e.toString(),
          isError: true,
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: context.widthPct(6)),
            child: SizedBox(
              height: context.heightPct(90), 
              child: Stack(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // 1. Back Button
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Padding(
                          padding: EdgeInsets.only(top: context.heightPct(2)),
                          child: IconButton(
                            onPressed: () {
                              if (_isOtpSent) {
                                setState(() => _isOtpSent = false);
                              } else {
                                context.pop();
                              }
                            },
                            icon: const Icon(Icons.arrow_back_rounded, color: Color(0xFF03081B)),
                          ),
                        ),
                      ),
                      
                      SizedBox(height: context.heightPct(4)),

                      // 2. Headline
                      Text(
                        'Let\'s get\nstarted',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: 'Monument',
                          fontSize: 40,
                          fontWeight: FontWeight.w600,
                          height: 1.1,
                          color: Color(0xFF03081B),
                        ),
                      ),

                      const Spacer(flex: 2),

                      // 3. Auth Form
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 300),
                        child: Column(
                          key: ValueKey<bool>(_isOtpSent),
                          children: [
                            if (!_isOtpSent)
                              TextFormField(
                                controller: _phoneController,
                                keyboardType: TextInputType.phone,
                                cursorColor: const Color(0xFF03081B),
                                enabled: !_isLoading,
                                style: GoogleFonts.inter(
                                  color: const Color(0xFF03081B),
                                  fontWeight: FontWeight.w500,
                                  fontSize: 16,
                                ),
                                inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
                                decoration: InputDecoration(
                                  labelText: 'Phone Number',
                                  prefixText: '+91 ',
                                  prefixStyle: GoogleFonts.inter(
                                    color: const Color(0xFF03081B),
                                    fontWeight: FontWeight.w500,
                                  ),
                                  labelStyle: GoogleFonts.inter(color: const Color(0xFF03081B).withOpacity(0.5)),
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: const BorderSide(color: Color(0xFFE5E5E5)),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: const BorderSide(color: Color(0xFF03081B)),
                                  ),
                                ),
                              )
                            else
                              Pinput(
                                length: 6,
                                controller: _otpController,
                                autofocus: true,
                                enabled: !_isLoading,
                                onCompleted: (pin) => _handleVerifyOtp(pin),
                                defaultPinTheme: PinTheme(
                                  width: 56,
                                  height: 60,
                                  textStyle: GoogleFonts.inter(
                                    fontSize: 22,
                                    color: const Color(0xFF03081B),
                                    fontWeight: FontWeight.w600,
                                  ),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: const Color(0xFFE5E5E5)),
                                  ),
                                ),
                                focusedPinTheme: PinTheme(
                                  width: 56,
                                  height: 60,
                                  textStyle: GoogleFonts.inter(
                                    fontSize: 22,
                                    color: const Color(0xFF03081B),
                                    fontWeight: FontWeight.w600,
                                  ),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: const Color(0xFF03081B), width: 2),
                                  ),
                                ),
                              ),
                            const SizedBox(height: 16),
                            SizedBox(
                              width: double.infinity,
                              height: 52,
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF03081B),
                                  foregroundColor: Colors.white,
                                  elevation: 0,
                                  shape: const StadiumBorder(),
                                ),
                                onPressed: _isLoading 
                                  ? null 
                                  : () {
                                      if (!_isOtpSent) {
                                        _handleRequestOtp();
                                      } else {
                                        _handleVerifyOtp(_otpController.text);
                                      }
                                    },
                                child: _isLoading 
                                  ? const SizedBox(
                                      height: 20, 
                                      width: 20, 
                                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                                    )
                                  : Text(
                                      _isOtpSent ? 'SIGN IN' : 'RECEIVE OTP',
                                      style: GoogleFonts.inter(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: 1.2,
                                      ),
                                    ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const Spacer(),

                      // 4. Divider
                      Row(
                        children: [
                          const Expanded(child: Divider(color: Color(0xFFE5E5E5))),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            child: Text(
                              'OR',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: const Color(0xFF03081B).withOpacity(0.4),
                              ),
                            ),
                          ),
                          const Expanded(child: Divider(color: Color(0xFFE5E5E5))),
                        ],
                      ),

                      const Spacer(),

                      // 5. Google Auth
                      SizedBox(
                        width: double.infinity,
                        height: 52,
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFE5E5E5)),
                            shape: const StadiumBorder(),
                            padding: const EdgeInsets.symmetric(horizontal: 24),
                          ),
                          onPressed: () {},
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const SizedBox(width: 24),
                              Text(
                                'CONTINUE WITH GOOGLE',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.2,
                                  color: const Color(0xFF03081B),
                                ),
                              ),
                              const Icon(Icons.g_mobiledata_rounded, color: Color(0xFF03081B), size: 28),
                            ],
                          ),
                        ),
                      ),

                      const Spacer(flex: 3),

                      // 6. Legal Footer
                      Padding(
                        padding: EdgeInsets.only(bottom: context.heightPct(4)),
                        child: RichText(
                          textAlign: TextAlign.center,
                          text: TextSpan(
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              height: 1.5,
                              color: const Color(0xFF03081B).withOpacity(0.5),
                            ),
                            children: [
                              const TextSpan(text: 'By continuing, you agree to our '),
                              _underlinedSpan('Terms'),
                              const TextSpan(text: ' and '),
                              _underlinedSpan('Privacy Policy'),
                              const TextSpan(text: '.'),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (_isLoading)
                    const Center(
                      child: CircularProgressIndicator(color: Color(0xFF03081B)),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  TextSpan _underlinedSpan(String text) {
    return TextSpan(
      text: text,
      style: const TextStyle(
        color: Color(0xFF03081B),
        fontWeight: FontWeight.w600,
        decoration: TextDecoration.underline,
      ),
    );
  }
}
