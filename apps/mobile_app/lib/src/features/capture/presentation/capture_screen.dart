import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:vibration/vibration.dart';
import 'dart:async';
import 'dart:math' as math;
import 'widgets/ar_bounding_box.dart';
import '../../../shared/theme/responsive_layout.dart';
import '../../reconstruction/data/project_repository.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

class CaptureScreen extends ConsumerStatefulWidget {
  final String projectName;
  const CaptureScreen({super.key, required this.projectName});

  @override
  ConsumerState<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends ConsumerState<CaptureScreen> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isAutoMode = true;
  int _photoCount = 0;
  final int _minPhotos = 10;
  final ImagePicker _picker = ImagePicker();
  bool _isCapturing = false;
  bool _isUploading = false;
  double _uploadProgress = 0;
  List<XFile> _capturedImages = [];
  String? _fcmToken;
  double _stability = 1.0; 
  StreamSubscription? _accelerometerSub;
  Timer? _autoCaptureTimer;
  
  double _pitch = 0;
  double _roll = 0;
  double _pulseValue = 0;
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _initSensors();
    _initNotifications();
  }

  Future<void> _initNotifications() async {
    FirebaseMessaging messaging = FirebaseMessaging.instance;
    NotificationSettings settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      _fcmToken = await FirebaseMessaging.instance.getToken();
      print('FCM Token: $_fcmToken');
      setState(() {});
    }
  }

  Future<void> _initCamera() async {
    _cameras = await availableCameras();
    if (_cameras != null && _cameras!.isNotEmpty) {
      _controller = CameraController(
        _cameras![0],
        ResolutionPreset.high,
        enableAudio: false,
      );
      await _controller!.initialize();
      if (mounted) setState(() {});
    }
  }

  void _initSensors() {
    _accelerometerSub = accelerometerEventStream().listen((event) {
      if (mounted) {
        setState(() {
          // Calculate pitch and roll from accelerometer for 3D visualization
          _pitch = math.atan2(event.y, event.z);
          _roll = math.atan2(event.x, math.sqrt(event.y * event.y + event.z * event.z));
          
          // Basic stability check
          double magnitude = (event.x.abs() + event.y.abs() + event.z.abs());
          _stability = (1.0 - (magnitude / 15.0)).clamp(0.0, 1.0);
        });
      }
    });
  }

  @override
  void dispose() {
    _controller?.dispose();
    _accelerometerSub?.cancel();
    _autoCaptureTimer?.cancel();
    super.dispose();
  }

  void _toggleMode() {
    setState(() {
      _isAutoMode = !_isAutoMode;
      if (!_isAutoMode) _stopAutoCapture();
    });
  }

  void _startAutoCapture() {
    setState(() => _isCapturing = true);
    _autoCaptureTimer = Timer.periodic(const Duration(milliseconds: 1000), (timer) {
      if (_stability > 0.7 && _photoCount < _minPhotos) {
        _takePhoto();
      }
    });
  }

  void _stopAutoCapture() {
    _autoCaptureTimer?.cancel();
    setState(() => _isCapturing = false);
  }

  Future<void> _pickFromGallery() async {
    final List<XFile> images = await _picker.pickMultiImage();
    if (images.isNotEmpty) {
      setState(() {
        _capturedImages.addAll(images);
        _photoCount = _capturedImages.length;
      });
      
      Vibration.vibrate(duration: 100);
      
      // Auto-finalize if they picked many? No, let's keep it manual as requested.
    }
  }

  Future<void> _takePhoto() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    try {
      final XFile image = await _controller!.takePicture();
      _capturedImages.add(image);
      
      if (await Vibration.hasVibrator() ?? false) {
        Vibration.vibrate(duration: 50);
      }

      if (mounted) {
        setState(() {
          _photoCount++;
        });
        
        if (_photoCount >= _minPhotos) {
          // In auto mode, we just stop the timer, but let the user decide when to process
          if (_isAutoMode) {
            _stopAutoCapture();
          }
        }
      }
    } catch (e) {
      debugPrint('Error taking photo: $e');
    }
  }

  Future<void> _finalizeCapture() async {
    setState(() => _isUploading = true);
    
    try {
      final repository = ref.read(projectRepositoryProvider);
      
      // 1. Create Project
      final projectId = await repository.createProject(
        name: widget.projectName,
        description: 'Captured via VokVision Pro',
        ownerPhone: '+918595192809', // Real user phone
        fcmToken: _fcmToken,
      );

      // 2. Upload Photos
      await repository.uploadPhotos(projectId, _capturedImages);

      if (mounted) {
        context.pushReplacement('/processing/$projectId', extra: widget.projectName);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isUploading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Upload failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(child: CircularProgressIndicator(color: Colors.white)),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          Center(
            child: CameraPreview(_controller!),
          ),

          if (_isUploading)
            Container(
              color: Colors.black.withOpacity(0.8),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const CircularProgressIndicator(color: Colors.white),
                    const SizedBox(height: 24),
                    Text(
                      'PROCESSING ASSETS',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 2.0,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Uploading ${widget.projectName}...',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: Colors.white.withOpacity(0.5),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          _buildAROverlay(),

          Positioned(
            top: 60,
            left: 24,
            right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildCircularButton(
                  icon: Icons.close_rounded,
                  onTap: () => context.pop(),
                ),
                _buildModeToggle(),
                _buildCircularButton(
                  icon: Icons.flash_on_rounded,
                  onTap: () {},
                ),
              ],
            ),
          ),

          Positioned(
            bottom: 40,
            left: 24,
            right: 24,
            child: Column(
              children: [
                _buildStabilityIndicator(),
                const SizedBox(height: 24),
                _buildCaptureControls(),
                const SizedBox(height: 24),
                _buildProgressCounter(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAROverlay() {
    return Center(
      child: CustomPaint(
        size: Size(context.widthPct(100), context.heightPct(100)),
        painter: ARBoundingBoxPainter(
          scale: 1.0,
          pulseValue: 1.0, 
          devicePitch: _pitch,
          deviceRoll: _roll,
        ),
      ),
    );
  }

  Widget _buildModeToggle() {
    return GestureDetector(
      onTap: _toggleMode,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.5),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Row(
          children: [
            Text(
              _isAutoMode ? 'AUTO' : 'MANUAL',
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: 2.0,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCircularButton({required IconData icon, required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.5),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _buildStabilityIndicator() {
    return Column(
      children: [
        Text(
          _stability > 0.7 ? 'STABLE' : 'KEEP STEADY',
          style: GoogleFonts.inter(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.0,
            color: _stability > 0.7 ? Colors.white : Colors.redAccent,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          width: 100,
          height: 2,
          color: Colors.white.withOpacity(0.1),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Container(
              width: 100 * _stability,
              height: 2,
              color: Colors.white,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCaptureControls() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        const SizedBox(width: 64), 
        GestureDetector(
          onTap: _isAutoMode 
            ? (_isCapturing ? _stopAutoCapture : _startAutoCapture)
            : _takePhoto,
          child: Container(
            width: 72,
            height: 72,
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 3),
            ),
            child: Container(
              decoration: BoxDecoration(
                color: _isCapturing ? Colors.redAccent : Colors.white,
                shape: BoxShape.circle,
              ),
              child: Icon(
                _isAutoMode 
                  ? (_isCapturing ? Icons.stop_rounded : Icons.play_arrow_rounded)
                  : Icons.camera_alt_rounded,
                color: _isCapturing ? Colors.white : Colors.black,
              ),
            ),
          ),
        ),
        _buildCircularButton(
          icon: Icons.photo_library_rounded,
          onTap: _pickFromGallery,
        ),
      ],
    );
  }

  Widget _buildProgressCounter() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          '$_photoCount',
          style: const TextStyle(
            fontFamily: 'Monument',
            fontSize: 14,
            color: Colors.white,
          ),
        ),
        Text(
          ' COMPLETED',
          style: TextStyle(
            fontFamily: 'Monument',
            fontSize: 14,
            color: Colors.white.withOpacity(0.3),
          ),
        ),
        if (_photoCount >= _minPhotos) ...[
          const SizedBox(width: 24),
          GestureDetector(
            onTap: _finalizeCapture,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(30),
                boxShadow: [
                  BoxShadow(
                    color: Colors.white.withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: Text(
                'PROCESS NOW',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  color: Colors.black,
                  letterSpacing: 1.5,
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
