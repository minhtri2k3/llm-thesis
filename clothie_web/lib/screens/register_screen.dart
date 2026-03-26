import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:clothie_web/config.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:clothie_web/widgets/flying_icon_bg.dart';
import 'package:clothie_web/screens/chat_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameController = TextEditingController();
  final _api = ApiService();
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _startChat() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      setState(() => _error = 'Please enter your name to continue.');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final sessionId = await _api.createSession(name);
      if (mounted) {
        Navigator.of(context).pushReplacement(
          PageRouteBuilder(
            transitionDuration: const Duration(milliseconds: 500),
            pageBuilder: (_, anim, __) =>
                ChatScreen(sessionId: sessionId, userName: name),
            transitionsBuilder: (_, anim, __, child) =>
                FadeTransition(opacity: anim, child: child),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = 'Failed to start session. Please try again.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(kBgColor),
      body: Stack(
        children: [
          const Positioned.fill(child: FlyingIconBackground(iconCount: 12)),
          // Dark overlay for readability
          Positioned.fill(
            child: Container(color: Colors.black.withOpacity(0.3)),
          ),
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: _buildCard(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCard() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 40),
      decoration: BoxDecoration(
        color: const Color(kSurfaceColor).withOpacity(0.85),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: const Color(kAccentLight).withOpacity(0.15),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.4),
            blurRadius: 40,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // App icon
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: const Color(kAccentColor).withOpacity(0.2),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: const Color(kAccentLight).withOpacity(0.3),
              ),
            ),
            child: const Center(child: Text('👗', style: TextStyle(fontSize: 30))),
          ),
          const SizedBox(height: 24),
          Text(
            'Welcome to Clothie',
            style: GoogleFonts.outfit(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: const Color(kTextPrimary),
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tell us your name to get started',
            style: GoogleFonts.outfit(
              fontSize: 14,
              color: const Color(kTextSecondary),
            ),
          ),
          const SizedBox(height: 32),

          // Name input
          TextField(
            controller: _nameController,
            autofocus: true,
            onSubmitted: (_) => _startChat(),
            style: GoogleFonts.outfit(
              color: const Color(kTextPrimary),
              fontSize: 15,
            ),
            decoration: InputDecoration(
              hintText: 'Enter your name',
              hintStyle: TextStyle(
                  color: const Color(kTextSecondary).withOpacity(0.7)),
              filled: true,
              fillColor: const Color(kCardColor),
              prefixIcon: const Icon(Icons.person_outline,
                  color: Color(kAccentLight), size: 20),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(
                    color: Colors.white.withOpacity(0.08), width: 1),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(
                    color: Color(kAccentLight), width: 1.5),
              ),
              errorText: _error,
              errorStyle:
                  const TextStyle(color: Color(0xFFEF4444), fontSize: 12),
            ),
          ),
          const SizedBox(height: 20),

          // CTA button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _startChat,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(kAccentColor),
                foregroundColor: Colors.white,
                disabledBackgroundColor:
                    const Color(kAccentColor).withOpacity(0.4),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
                elevation: 0,
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : Text(
                      'Start Chatting  →',
                      style: GoogleFonts.outfit(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.3,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
