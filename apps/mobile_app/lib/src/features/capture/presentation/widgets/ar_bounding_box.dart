import 'package:flutter/material.dart';
import 'dart:math' as math;

class ARBoundingBoxPainter extends CustomPainter {
  final double scale;
  final double pulseValue;
  final double devicePitch; // From sensors
  final double deviceRoll;  // From sensors

  ARBoundingBoxPainter({
    required this.scale,
    required this.pulseValue,
    this.devicePitch = 0,
    this.deviceRoll = 0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    final glowPaint = Paint()
      ..color = Colors.white.withOpacity(0.2 * pulseValue)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.0
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    final center = Offset(size.width / 2, size.height / 2);
    final boxSize = size.width * 0.6 * scale;

    // Perspective projection logic (simplified for pseudo-3D)
    // We calculate 8 corners of a cube and rotate them based on device tilt
    List<Offset> corners = _calculateProjectedCorners(center, boxSize, devicePitch, deviceRoll);

    // Draw the 12 edges of the cube
    _drawCubeEdges(canvas, corners, paint, glowPaint);
    
    // Draw corner accents for high-tech look
    _drawCornerBrackets(canvas, corners, Colors.white);
  }

  List<Offset> _calculateProjectedCorners(Offset center, double size, double pitch, double roll) {
    final half = size / 2;
    // 3D coordinates: [x, y, z]
    List<List<double>> vertices = [
      [-half, -half, -half], [half, -half, -half], [half, half, -half], [-half, half, -half],
      [-half, -half, half], [half, -half, half], [half, half, half], [-half, half, half],
    ];

    return vertices.map((v) {
      double x = v[0];
      double y = v[1];
      double z = v[2];

      // Rotation around X (pitch)
      double tempY = y * math.cos(pitch) - z * math.sin(pitch);
      double tempZ = y * math.sin(pitch) + z * math.cos(pitch);
      y = tempY;
      z = tempZ;

      // Rotation around Y (roll simulation)
      double tempX = x * math.cos(roll) + z * math.sin(roll);
      z = -x * math.sin(roll) + z * math.cos(roll);
      x = tempX;

      // Simple perspective projection
      double perspective = 1.0 / (1.0 - z / 1000.0);
      return Offset(center.dx + x * perspective, center.dy + y * perspective);
    }).toList();
  }

  void _drawCubeEdges(Canvas canvas, List<Offset> c, Paint main, Paint glow) {
    final List<List<int>> connections = [
      [0, 1], [1, 2], [2, 3], [3, 0], // Back face
      [4, 5], [5, 6], [6, 7], [7, 4], // Front face
      [0, 4], [1, 5], [2, 6], [3, 7], // Connecting edges
    ];

    for (var edge in connections) {
      canvas.drawLine(c[edge[0]], c[edge[1]], glow);
      canvas.drawLine(c[edge[0]], c[edge[1]], main);
    }
  }

  void _drawCornerBrackets(Canvas canvas, List<Offset> c, Color color) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    // Draw small accents at each corner
    for (var corner in c) {
      canvas.drawCircle(corner, 2, paint..style = PaintingStyle.fill);
    }
  }

  @override
  bool shouldRepaint(covariant ARBoundingBoxPainter oldDelegate) => true;
}
