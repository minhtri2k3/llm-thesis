import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:clothie_web/widgets/star_rating.dart';
import 'package:clothie_web/screens/splash_screen.dart';

class RatingScreen extends StatefulWidget {
  final String sessionId;
  final String userName;

  const RatingScreen({
    super.key,
    required this.sessionId,
    required this.userName,
  });

  @override
  State<RatingScreen> createState() => _RatingScreenState();
}

class _RatingScreenState extends State<RatingScreen> {
  final _feedbackController = TextEditingController();
  final _api = ApiService();
  int _rating = 0;
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _feedbackController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == 0) {
      setState(() => _error = 'Please select a rating.');
      return;
    }
    if (_feedbackController.text.trim().isEmpty) {
      setState(() => _error = 'Please share some feedback.');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await _api.submitRating(
        sessionId: widget.sessionId,
        rating: _rating,
        feedback: _feedbackController.text.trim(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Thank you, ${widget.userName}! 🙏',
              style: GoogleFonts.outfit(fontSize: 14),
            ),
            backgroundColor: Theme.of(context).snackBarTheme.backgroundColor ?? Theme.of(context).colorScheme.primary,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10)),
          ),
        );
        await Future.delayed(const Duration(milliseconds: 1500));
        if (mounted) {
          Navigator.of(context).pushAndRemoveUntil(
            PageRouteBuilder(
              transitionDuration: const Duration(milliseconds: 600),
              pageBuilder: (_, anim, __) => const SplashScreen(),
              transitionsBuilder: (_, anim, __, child) =>
                  FadeTransition(opacity: anim, child: child),
            ),
            (_) => false,
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = 'Submission failed. Please try again.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              theme.scaffoldBackgroundColor,
              theme.colorScheme.primary.withValues(alpha: 0.08),
              theme.scaffoldBackgroundColor,
            ],
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                   // Header
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: theme.colorScheme.primary.withValues(alpha: 0.3)),
                    ),
                    child: const Center(
                      child: Text('⭐', style: TextStyle(fontSize: 34)),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'How was your experience?',
                    style: GoogleFonts.outfit(
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      color: theme.colorScheme.onSurface,
                      letterSpacing: -0.5,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Your feedback helps improve Clothie',
                    style: GoogleFonts.outfit(
                      fontSize: 14,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),

                  const SizedBox(height: 36),

                  // Rating card
                  Container(
                    padding: const EdgeInsets.all(28),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: isDark ? Colors.white.withValues(alpha: 0.07) : Colors.black.withValues(alpha: 0.07)),
                    ),
                    child: Column(
                      children: [
                        Text(
                          _rating == 0
                              ? 'Select a score (1–10)'
                              : 'Your score: $_rating / 10',
                          style: GoogleFonts.outfit(
                            fontSize: 13,
                            color: _rating == 0
                                ? theme.colorScheme.onSurface.withValues(alpha: 0.6)
                                : theme.colorScheme.primary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 16),
                        StarRating(
                          value: _rating,
                          onChanged: (v) =>
                              setState(() => _rating = v),
                        ),
                        const SizedBox(height: 28),

                        // Feedback text
                        TextField(
                          controller: _feedbackController,
                          maxLines: 4,
                          style: GoogleFonts.outfit(
                            color: theme.colorScheme.onSurface,
                            fontSize: 14,
                          ),
                          decoration: InputDecoration(
                            hintText:
                                'What did you think about this system?',
                            hintStyle: TextStyle(
                                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                                fontSize: 13),
                            filled: true,
                            fillColor: theme.inputDecorationTheme.fillColor ?? theme.colorScheme.surface,
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color: isDark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.08)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color: theme.colorScheme.primary, width: 1.5),
                            ),
                          ),
                        ),

                        if (_error != null) ...[
                          const SizedBox(height: 10),
                          Text(_error!,
                              style: const TextStyle(
                                  color: Color(0xFFEF4444), fontSize: 12)),
                        ],

                        const SizedBox(height: 20),

                        // Submit button
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _submit,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: theme.colorScheme.primary,
                              foregroundColor: theme.scaffoldBackgroundColor,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14)),
                              elevation: 0,
                            ),
                            child: _isLoading
                                ? SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: theme.scaffoldBackgroundColor),
                                  )
                                : Text(
                                    'Submit Feedback',
                                    style: GoogleFonts.outfit(
                                      fontSize: 15,
                                      fontWeight: FontWeight.w600,
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
          ),
        ),
      ),
    );
  }
}

/// Modal dialog version of the rating flow — shown from within [ChatScreen].
///
/// On successful submission, calls [onComplete] so the parent can
/// navigate to [SplashScreen].
class RatingDialog extends StatefulWidget {
  final String sessionId;
  final String userName;
  final VoidCallback onComplete;

  const RatingDialog({
    super.key,
    required this.sessionId,
    required this.userName,
    required this.onComplete,
  });

  @override
  State<RatingDialog> createState() => _RatingDialogState();
}

class _RatingDialogState extends State<RatingDialog> {
  final _feedbackController = TextEditingController();
  final _api = ApiService();
  int _rating = 0;
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _feedbackController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == 0) {
      setState(() => _error = 'Please select a rating.');
      return;
    }
    if (_feedbackController.text.trim().isEmpty) {
      setState(() => _error = 'Please share some feedback.');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await _api.submitRating(
        sessionId: widget.sessionId,
        rating: _rating,
        feedback: _feedbackController.text.trim(),
      );
      if (mounted) Navigator.of(context).pop();
      widget.onComplete();
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = 'Submission failed. Try again.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Dialog(
      backgroundColor: theme.colorScheme.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('⭐', style: TextStyle(fontSize: 40)),
              const SizedBox(height: 12),
              Text(
                'How was your experience?',
                style: GoogleFonts.outfit(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                'Hi ${widget.userName}, your feedback helps improve Clothie.',
                style: GoogleFonts.outfit(
                    fontSize: 13, color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              Text(
                _rating == 0
                    ? 'Select a score (1–10)'
                    : 'Your score: $_rating / 10',
                style: GoogleFonts.outfit(
                  fontSize: 13,
                  color: _rating == 0
                      ? theme.colorScheme.onSurface.withValues(alpha: 0.6)
                      : theme.colorScheme.primary,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 12),
              StarRating(
                value: _rating,
                onChanged: (v) => setState(() => _rating = v),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _feedbackController,
                maxLines: 3,
                style: GoogleFonts.outfit(
                    color: theme.colorScheme.onSurface, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'What did you think about this system?',
                  hintStyle: TextStyle(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                      fontSize: 13),
                  filled: true,
                  fillColor: theme.inputDecorationTheme.fillColor ?? theme.colorScheme.surface,
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide:
                        BorderSide(color: isDark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.08)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(
                        color: theme.colorScheme.primary, width: 1.5),
                  ),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!,
                    style: const TextStyle(
                        color: Color(0xFFEF4444), fontSize: 12)),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                height: 46,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: theme.colorScheme.primary,
                    foregroundColor: theme.scaffoldBackgroundColor,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    elevation: 0,
                  ),
                  child: _isLoading
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: theme.scaffoldBackgroundColor),
                        )
                      : Text('Submit Feedback',
                          style: GoogleFonts.outfit(
                              fontSize: 14, fontWeight: FontWeight.w600)),
                ),
              ),
              TextButton(
                onPressed: _isLoading
                    ? null
                    : () => Navigator.of(context).pop(),
                child: Text('Maybe later',
                    style: GoogleFonts.outfit(
                        fontSize: 12,
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
