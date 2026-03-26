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

  Future<void> _showLeaderboard() async {
    showDialog(
      context: context,
      builder: (_) => _LeaderboardDialog(api: _api),
    );
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
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildCard(),
                    const SizedBox(height: 20),
                    // ── Leaderboard link ──────────────────────────────────
                    GestureDetector(
                      onTap: _showLeaderboard,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(kSurfaceColor).withOpacity(0.6),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: const Color(kAccentLight).withOpacity(0.15),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('🏆',
                                style: TextStyle(fontSize: 18)),
                            const SizedBox(width: 10),
                            Text(
                              'Leaderboard',
                              style: GoogleFonts.outfit(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: const Color(kAccentLight),
                                letterSpacing: 0.3,
                              ),
                            ),
                            const SizedBox(width: 6),
                            const Icon(Icons.arrow_forward_ios_rounded,
                                size: 12, color: Color(kAccentLight)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
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

// ─── Leaderboard Dialog ────────────────────────────────────────────────────────

class _LeaderboardDialog extends StatefulWidget {
  final ApiService api;
  const _LeaderboardDialog({required this.api});

  @override
  State<_LeaderboardDialog> createState() => _LeaderboardDialogState();
}

class _LeaderboardDialogState extends State<_LeaderboardDialog> {
  List<Map<String, dynamic>>? _entries;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.api.getRatings();
      if (mounted) setState(() => _entries = data);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 440, maxHeight: 580),
        decoration: BoxDecoration(
          color: const Color(kSurfaceColor),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
              color: const Color(kAccentLight).withOpacity(0.15), width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.5),
              blurRadius: 40,
              spreadRadius: 0,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Row(
                children: [
                  const Text('🏆', style: TextStyle(fontSize: 22)),
                  const SizedBox(width: 10),
                  Text(
                    'Session Feedback',
                    style: GoogleFonts.outfit(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: const Color(kTextPrimary),
                    ),
                  ),
                  const Spacer(),
                  GestureDetector(
                    onTap: () => Navigator.of(context).pop(),
                    child: const Icon(Icons.close_rounded,
                        color: Color(kTextSecondary), size: 20),
                  ),
                ],
              ),
            ),
            const Divider(color: Color(0x22FFFFFF), height: 1),

            // Body
            Flexible(
              child: _error != null
                  ? Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(_error!,
                          style: const TextStyle(
                              color: Color(0xFFEF4444), fontSize: 13)),
                    )
                  : _entries == null
                      ? const Padding(
                          padding: EdgeInsets.all(40),
                          child: CircularProgressIndicator(
                              color: Color(kAccentLight)),
                        )
                      : _entries!.isEmpty
                          ? Padding(
                              padding: const EdgeInsets.all(40),
                              child: Text(
                                'No feedback submitted yet.\nBe the first!',
                                textAlign: TextAlign.center,
                                style: GoogleFonts.outfit(
                                  color: const Color(kTextSecondary),
                                  fontSize: 14,
                                ),
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 20, vertical: 16),
                              itemCount: _entries!.length,
                              separatorBuilder: (_, __) => const Divider(
                                  color: Color(0x15FFFFFF), height: 1),
                              itemBuilder: (_, i) {
                                final e = _entries![i];
                                final rating =
                                    (e['rating'] as num?)?.toInt() ?? 0;
                                final name =
                                    e['user_name'] as String? ?? 'Anonymous';
                                final feedback =
                                    e['feedback'] as String? ?? '';
                                return Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 12),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      // Rank medal or number
                                      SizedBox(
                                        width: 28,
                                        child: Text(
                                          i == 0
                                              ? '🥇'
                                              : i == 1
                                                  ? '🥈'
                                                  : i == 2
                                                      ? '🥉'
                                                      : '${i + 1}.',
                                          style: TextStyle(
                                            fontSize: i < 3 ? 18 : 13,
                                            color:
                                                const Color(kTextSecondary),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                Text(
                                                  name,
                                                  style: GoogleFonts.outfit(
                                                    fontSize: 14,
                                                    fontWeight: FontWeight.w600,
                                                    color: const Color(
                                                        kTextPrimary),
                                                  ),
                                                ),
                                                const Spacer(),
                                                // Star rating
                                                _StarRating(rating: rating),
                                                const SizedBox(width: 4),
                                                Text(
                                                  '$rating/10',
                                                  style: GoogleFonts.outfit(
                                                    fontSize: 12,
                                                    color: const Color(
                                                        kAccentLight),
                                                    fontWeight:
                                                        FontWeight.w600,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            if (feedback.isNotEmpty) ...[
                                              const SizedBox(height: 4),
                                              Text(
                                                '"$feedback"',
                                                style: GoogleFonts.outfit(
                                                  fontSize: 13,
                                                  color: const Color(
                                                      kTextSecondary),
                                                  fontStyle: FontStyle.italic,
                                                  height: 1.5,
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
            ),

            // Close button
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: TextButton.styleFrom(
                    foregroundColor: const Color(kAccentLight),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                  child: Text('Close',
                      style: GoogleFonts.outfit(
                          fontSize: 14, fontWeight: FontWeight.w500)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact 5-star visual for a 1–10 rating (half-star granularity).
class _StarRating extends StatelessWidget {
  final int rating;
  const _StarRating({required this.rating});

  @override
  Widget build(BuildContext context) {
    // Map 0-10 to 0-5 stars
    final stars = rating / 2;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (i) {
        IconData icon;
        if (stars >= i + 1) {
          icon = Icons.star_rounded;
        } else if (stars >= i + 0.5) {
          icon = Icons.star_half_rounded;
        } else {
          icon = Icons.star_outline_rounded;
        }
        return Icon(icon, size: 14, color: const Color(0xFFFBBF24));
      }),
    );
  }
}
