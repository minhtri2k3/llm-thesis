import 'dart:math';
import 'package:flutter/material.dart';

/// Animated background with randomly flying cloth emoji icons.
///
/// Each icon moves at an independent velocity and wraps around screen edges,
/// creating a continuous parallax-like ambient animation.
class FlyingIconBackground extends StatefulWidget {
  final int iconCount;
  const FlyingIconBackground({super.key, this.iconCount = 14});

  @override
  State<FlyingIconBackground> createState() => _FlyingIconBackgroundState();
}

class _FlyingIconBackgroundState extends State<FlyingIconBackground>
    with TickerProviderStateMixin {
  late AnimationController _controller;
  late List<_IconParticle> _particles;
  final _rng = Random();

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat();

    _controller.addListener(_tick);
  }

  void _initParticles(Size size) {
    _particles = List.generate(widget.iconCount, (_) => _IconParticle(
      x: _rng.nextDouble() * size.width,
      y: _rng.nextDouble() * size.height,
      dx: (_rng.nextDouble() - 0.5) * 1.2,
      dy: (_rng.nextDouble() - 0.5) * 1.2,
      size: 18 + _rng.nextDouble() * 22,
      opacity: 0.06 + _rng.nextDouble() * 0.14,
      icon: _icons[_rng.nextInt(_icons.length)],
    ));
  }

  static const _icons = ['👗', '👠', '👜', '🧥', '👒'];

  void _tick() {
    if (!mounted || _particles.isEmpty) return;
    final size = MediaQuery.sizeOf(context);
    for (final p in _particles) {
      p.x += p.dx;
      p.y += p.dy;
      // Wrap around edges
      if (p.x < -50) p.x = size.width + 50;
      if (p.x > size.width + 50) p.x = -50;
      if (p.y < -50) p.y = size.height + 50;
      if (p.y > size.height + 50) p.y = -50;
    }
    setState(() {});
  }

  @override
  void dispose() {
    _controller.removeListener(_tick);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final size = Size(constraints.maxWidth, constraints.maxHeight);
      if (_particles.isEmpty || _particles.length != widget.iconCount) {
        _initParticles(size);
      }
      return CustomPaint(
        size: size,
        painter: _ParticlePainter(_particles),
      );
    });
  }
}

class _IconParticle {
  double x, y, dx, dy, size, opacity;
  final String icon;
  _IconParticle({
    required this.x,
    required this.y,
    required this.dx,
    required this.dy,
    required this.size,
    required this.opacity,
    required this.icon,
  });
}

class _ParticlePainter extends CustomPainter {
  final List<_IconParticle> particles;
  _ParticlePainter(this.particles);

  @override
  void paint(Canvas canvas, Size size) {
    for (final p in particles) {
      final textPainter = TextPainter(
        text: TextSpan(
          text: p.icon,
          style: TextStyle(fontSize: p.size),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      canvas.saveLayer(
        Rect.fromLTWH(p.x, p.y, p.size, p.size),
        Paint()..color = Colors.white.withOpacity(p.opacity),
      );
      textPainter.paint(canvas, Offset(p.x, p.y));
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ParticlePainter old) => true;
}
