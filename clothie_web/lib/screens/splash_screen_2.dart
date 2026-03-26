import 'dart:async';
import 'dart:math';

import 'package:carrots_hackathon/core/router/routes.dart';
import 'package:flutter/material.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _mainController;
  late AnimationController _flyingController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;

  // Random data for flying objects
  final List<IconData> _flyingIcons = [
    Icons.code,
    Icons.coffee,
    Icons.bug_report,
    Icons.timer,
    Icons.bolt,
    Icons.laptop_mac,
  ];
  final List<_FlyingObject> _objects = [];

  @override
  void initState() {
    super.initState();

    // 1. Setup Main Controller (Text & Logo entrance)
    _mainController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );

    // 2. Setup Flying Objects Controller (Continuous loop)
    _flyingController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    // Generate random flying objects
    final random = Random();
    for (int i = 0; i < 15; i++) {
      _objects.add(_FlyingObject(
        icon: _flyingIcons[random.nextInt(_flyingIcons.length)],
        startX: random.nextDouble(), // 0.0 to 1.0 (screen width ratio)
        // Use integer speeds (1.0 or 2.0) to ensure the loop is seamless
        // when the controller resets from 1.0 back to 0.0.
        speed: (1 + random.nextInt(2)).toDouble(),
        size: 15.0 + random.nextDouble() * 20.0, // Random size
        initialOffset: random.nextDouble(), // Start at different times
      ));
    }

    // 3. Define Scale Animation
    _scaleAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _mainController, curve: Curves.easeOutBack),
    );

    // 4. Define Opacity Animation
    _opacityAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _mainController, curve: Curves.easeIn),
    );

    // 5. Start main animation
    _mainController.forward();

    // 6. Navigate to Paywall Screen after 3.5 seconds
    Timer(const Duration(milliseconds: 3500), () {
      if (mounted) {
        // Ensure appRouter is imported from your routes file
        appRouter.go('/paywall');
      }
    });
  }

  @override
  void dispose() {
    _mainController.dispose();
    _flyingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Get screen size for calculations
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // --- Layer 1: Flying Objects Background ---
          // Use Positioned.fill to ensure the builder takes up the whole screen space
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _flyingController,
              builder: (context, child) {
                return Stack(
                  // IMPORTANT: fit: StackFit.expand ensures the stack fills the area
                  // otherwise it might shrink to 0x0 if children are Positioned.
                  fit: StackFit.expand,
                  children: _objects.map((obj) {
                    // Calculate dynamic position
                    // Loops the value from 0 to 1 repeatedly based on controller + offset
                    final progress = (_flyingController.value * obj.speed +
                            obj.initialOffset) %
                        1.0;

                    // Invert progress so they fly UP (1.0 -> 0.0)
                    final topPosition = size.height * (1.0 - progress);

                    // Add a slight sine wave horizontal movement
                    final leftPosition = (obj.startX * size.width) +
                        (sin(_flyingController.value * 2 * pi * obj.speed) *
                            20);

                    final opacity = 1.0 -
                        (progress < 0.2 ? (0.2 - progress) * 5 : 0.0) -
                        (progress > 0.8 ? (progress - 0.8) * 5 : 0.0);

                    return Positioned(
                      top: topPosition - 50, // Start slightly below screen
                      left: leftPosition,
                      child: Opacity(
                        opacity: opacity.clamp(0.0, 0.4), // Keep them subtle
                        child: Icon(
                          obj.icon,
                          color: Colors.greenAccent.withOpacity(0.5),
                          size: obj.size,
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ),

          // --- Layer 2: Main Content (Centered) ---
          Center(
            child: AnimatedBuilder(
              animation: _mainController,
              builder: (context, child) {
                return Opacity(
                  opacity: _opacityAnimation.value,
                  child: Transform.scale(
                    scale: _scaleAnimation.value,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Container for the main icon with a slight glow effect
                        Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.greenAccent.withOpacity(0.3),
                                blurRadius: 30,
                                spreadRadius: 5,
                              )
                            ],
                          ),
                          child: const Icon(
                            Icons
                                .rocket_launch_rounded, // Changed to rocket for "speed"
                            color: Colors.greenAccent,
                            size: 90,
                          ),
                        ),
                        const SizedBox(height: 30),
                        // Corrected Text
                        const Text(
                          "Crunch Time",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.greenAccent,
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 2.0,
                          ),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          "5 Hours Left\nTo Finish This Hackathon",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w600,
                            height: 1.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// Helper class to store state for each flying particle
class _FlyingObject {
  final IconData icon;
  final double startX; // Horizontal start position (0.0 to 1.0)
  final double speed; // How fast it moves
  final double size; // Icon size
  final double initialOffset; // Stagger start times

  _FlyingObject({
    required this.icon,
    required this.startX,
    required this.speed,
    required this.size,
    required this.initialOffset,
  });
}
