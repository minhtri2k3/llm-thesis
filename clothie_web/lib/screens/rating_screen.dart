import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:clothie_web/widgets/star_rating.dart';
import 'package:clothie_web/screens/register_screen.dart';

// ── Shared question data ─────────────────────────────────────────────────────

const _kQuestions = [
  (
    label: 'Overall experience',
    emoji: '🌟',
    hint: 'How would you rate the overall session?',
  ),
  (
    label: 'Suggestion quality',
    emoji: '🎯',
    hint: 'Were the product suggestions relevant and correct?',
  ),
  (
    label: 'Conversation naturalness',
    emoji: '💬',
    hint: 'How natural and helpful was the conversation flow?',
  ),
];

// ── Stand-alone RatingScreen ─────────────────────────────────────────────────

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
  final _ratings = [0, 0, 0]; // [overall, suggestions, conversation]
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _feedbackController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_ratings.any((r) => r == 0)) {
      setState(() => _error = 'Please rate all three questions.');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await _api.submitRating(
        sessionId: widget.sessionId,
        ratingOverall: _ratings[0],
        ratingSuggestions: _ratings[1],
        ratingConversation: _ratings[2],
        feedback: _feedbackController.text.trim(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Thank you, ${widget.userName}! 🙏',
              style: GoogleFonts.outfit(fontSize: 14),
            ),
            backgroundColor:
                Theme.of(context).snackBarTheme.backgroundColor ??
                    Theme.of(context).colorScheme.primary,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
        await Future.delayed(const Duration(milliseconds: 1500));
        if (mounted) {
          Navigator.of(context).pushAndRemoveUntil(
            PageRouteBuilder(
              transitionDuration: const Duration(milliseconds: 600),
              pageBuilder: (_, anim, __) => const RegisterScreen(),
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
                          color:
                              theme.colorScheme.primary.withValues(alpha: 0.3)),
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

                  // Three rating questions
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.07)
                              : Colors.black.withValues(alpha: 0.07)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (int i = 0; i < _kQuestions.length; i++) ...[
                          if (i > 0) const SizedBox(height: 24),
                          _RatingQuestion(
                            emoji: _kQuestions[i].emoji,
                            label: _kQuestions[i].label,
                            hint: _kQuestions[i].hint,
                            value: _ratings[i],
                            onChanged: (v) =>
                                setState(() => _ratings[i] = v),
                          ),
                        ],

                        const SizedBox(height: 24),
                        const Divider(),
                        const SizedBox(height: 16),

                        // Optional feedback field
                        Text(
                          'Additional comments (optional)',
                          style: GoogleFonts.outfit(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.onSurface
                                .withValues(alpha: 0.8),
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _feedbackController,
                          maxLines: 3,
                          style: GoogleFonts.outfit(
                            color: theme.colorScheme.onSurface,
                            fontSize: 14,
                          ),
                          decoration: InputDecoration(
                            hintText: 'What else would you like to share?',
                            hintStyle: TextStyle(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.4),
                                fontSize: 13),
                            filled: true,
                            fillColor:
                                theme.inputDecorationTheme.fillColor ??
                                    theme.colorScheme.surface,
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color: isDark
                                      ? Colors.white.withValues(alpha: 0.08)
                                      : Colors.black
                                          .withValues(alpha: 0.08)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color: theme.colorScheme.primary,
                                  width: 1.5),
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

// ── Modal (dialog) version ────────────────────────────────────────────────────

/// Modal dialog rating flow — shown from within [ChatScreen].
///
/// On successful submission, calls [onComplete] so the parent can navigate.
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
  final _ratings = [0, 0, 0]; // [overall, suggestions, conversation]
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _feedbackController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_ratings.any((r) => r == 0)) {
      setState(() => _error = 'Please rate all three questions.');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await _api.submitRating(
        sessionId: widget.sessionId,
        ratingOverall: _ratings[0],
        ratingSuggestions: _ratings[1],
        ratingConversation: _ratings[2],
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
          constraints: const BoxConstraints(maxWidth: 440),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Dialog header
                Row(
                  children: [
                    const Text('⭐', style: TextStyle(fontSize: 28)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Rate your experience',
                            style: GoogleFonts.outfit(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                          Text(
                            'Hi ${widget.userName} — 3 quick questions',
                            style: GoogleFonts.outfit(
                                fontSize: 12,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.6)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Three questions
                for (int i = 0; i < _kQuestions.length; i++) ...[
                  if (i > 0) const SizedBox(height: 16),
                  _RatingQuestion(
                    emoji: _kQuestions[i].emoji,
                    label: _kQuestions[i].label,
                    hint: _kQuestions[i].hint,
                    value: _ratings[i],
                    compact: true,
                    onChanged: (v) => setState(() => _ratings[i] = v),
                  ),
                ],

                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 12),

                // Optional feedback
                TextField(
                  controller: _feedbackController,
                  maxLines: 2,
                  style: GoogleFonts.outfit(
                      color: theme.colorScheme.onSurface, fontSize: 13),
                  decoration: InputDecoration(
                    hintText:
                        'Any other thoughts? (optional)',
                    hintStyle: TextStyle(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.4),
                        fontSize: 13),
                    filled: true,
                    fillColor: theme.inputDecorationTheme.fillColor ??
                        theme.colorScheme.surface,
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.08)
                              : Colors.black.withValues(alpha: 0.08)),
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
                const SizedBox(height: 16),

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
                                strokeWidth: 2,
                                color: theme.scaffoldBackgroundColor),
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
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.6))),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Shared sub-widget ─────────────────────────────────────────────────────────

class _RatingQuestion extends StatelessWidget {
  final String emoji;
  final String label;
  final String hint;
  final int value;
  final ValueChanged<int> onChanged;
  final bool compact;

  const _RatingQuestion({
    required this.emoji,
    required this.label,
    required this.hint,
    required this.value,
    required this.onChanged,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(emoji, style: TextStyle(fontSize: compact ? 16 : 18)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                label,
                style: GoogleFonts.outfit(
                  fontSize: compact ? 13 : 14,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurface,
                ),
              ),
            ),
            if (value > 0)
              Text(
                '$value / 5',
                style: GoogleFonts.outfit(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.primary,
                ),
              ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          hint,
          style: GoogleFonts.outfit(
            fontSize: compact ? 11 : 12,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
          ),
        ),
        const SizedBox(height: 10),
        StarRating(
          maxStars: 5,
          value: value,
          onChanged: onChanged,
        ),
      ],
    );
  }
}
