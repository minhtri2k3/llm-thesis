import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:clothie_web/extension/theme_provider.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:clothie_web/widgets/flying_icon_bg.dart';
import 'package:clothie_web/router/app_router.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameController = TextEditingController();
  final _yearController = TextEditingController();
  final _api = ApiService();
  bool _isLoading = false;
  String? _error;
  String? _selectedGender; // 'male' or 'female'

  @override
  void dispose() {
    _nameController.dispose();
    _yearController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _startChat() async {
    final name = _nameController.text.trim();
    final yearStr = _yearController.text.trim();
    final currentYear = DateTime.now().year;

    if (name.isEmpty) {
      setState(() => _error = 'Please enter your name to continue.');
      return;
    }
    final yearInt = int.tryParse(yearStr);
    if (yearInt == null || yearInt < 1900 || yearInt > currentYear) {
      setState(
        () => _error = 'Please enter a valid birth year (1900–$currentYear).',
      );
      return;
    }
    if (_selectedGender == null) {
      setState(() => _error = 'Please select your gender.');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final result = await _api.createSessionFull(
        name,
        yearInt,
        _selectedGender!,
        'gemini-2.5-flash',
      );
      if (mounted) {
        context.goNamed(
          'chat',
          extra: ChatRouteArgs(
            sessionId: result.sessionId,
            userName: name,
            agentCodename: result.cohortActive ? result.agentCodename : null,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = e.toString().contains('Cohort study already completed')
              ? 'You have already completed all 4 cohort sessions for this name. '
                'Please use a different name.'
              : 'Failed to start session. Please try again.';
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

  Future<void> _showProfessorPin() async {
    final secretKey = await showDialog<String>(
      context: context,
      builder: (_) => _PinDialog(api: _api),
    );
    if (secretKey != null && mounted) {
      context.goNamed(
        'professor-dashboard',
        extra: ProfessorDashboardRouteArgs(secretKey: secretKey),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          Consumer<ThemeProvider>(
            builder: (context, themeProvider, child) {
              return IconButton(
                icon: Icon(
                  themeProvider.isDarkMode
                      ? Icons.light_mode_rounded
                      : Icons.dark_mode_rounded,
                ),
                color: Theme.of(context).colorScheme.onSurface,
                onPressed: () {
                  themeProvider.toggleTheme();
                },
              );
            },
          ),
          const SizedBox(width: 16),
        ],
      ),
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
                          horizontal: 20,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(
                            context,
                          ).colorScheme.surface.withOpacity(0.6),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: Theme.of(
                              context,
                            ).colorScheme.secondary.withOpacity(0.15),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('🏆', style: TextStyle(fontSize: 18)),
                            const SizedBox(width: 10),
                            Text(
                              'Leaderboard',
                              style: GoogleFonts.outfit(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Theme.of(context).colorScheme.secondary,
                                letterSpacing: 0.3,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Icon(
                              Icons.arrow_forward_ios_rounded,
                              size: 12,
                              color: Theme.of(context).colorScheme.secondary,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    // ── Professor View link ──────────────────────────────
                    GestureDetector(
                      onTap: _showProfessorPin,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(
                            context,
                          ).colorScheme.surface.withOpacity(0.6),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: Theme.of(
                              context,
                            ).colorScheme.secondary.withOpacity(0.15),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('🔬', style: TextStyle(fontSize: 18)),
                            const SizedBox(width: 10),
                            Text(
                              'Professor View',
                              style: GoogleFonts.outfit(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Theme.of(context).colorScheme.secondary,
                                letterSpacing: 0.3,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Icon(
                              Icons.lock_outline_rounded,
                              size: 12,
                              color: Theme.of(context).colorScheme.secondary,
                            ),
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
        color: Theme.of(context).colorScheme.surface.withOpacity(0.85),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Theme.of(context).colorScheme.secondary.withOpacity(0.15),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
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
              color: Theme.of(context).colorScheme.primary.withOpacity(0.2),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: Theme.of(context).colorScheme.secondary.withOpacity(0.3),
              ),
            ),
            child: const Center(
              child: Text('👗', style: TextStyle(fontSize: 30)),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Welcome to Clothie',
            style: GoogleFonts.outfit(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: Theme.of(context).colorScheme.onSurface,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tell us a bit about yourself to get started',
            style: GoogleFonts.outfit(
              fontSize: 14,
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 32),

          // Name input
          TextField(
            controller: _nameController,
            autofocus: true,
            onSubmitted: (_) => _startChat(),
            style: GoogleFonts.outfit(
              color: Theme.of(context).colorScheme.onSurface,
              fontSize: 15,
            ),
            decoration: InputDecoration(
              hintText: 'Enter your name',
              hintStyle: TextStyle(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
              ),
              filled: true,
              fillColor: Theme.of(context).inputDecorationTheme.fillColor,
              prefixIcon: Icon(
                Icons.person_outline,
                color: Theme.of(context).colorScheme.secondary,
                size: 20,
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withOpacity(0.1),
                  width: 1,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(
                  color: Theme.of(context).colorScheme.secondary,
                  width: 1.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Birth year input
          TextField(
            controller: _yearController,
            keyboardType: TextInputType.number,
            maxLength: 4,
            style: GoogleFonts.outfit(
              color: Theme.of(context).colorScheme.onSurface,
              fontSize: 15,
            ),
            decoration: InputDecoration(
              hintText: 'Year of birth (e.g. 2000)',
              hintStyle: TextStyle(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
              ),
              filled: true,
              fillColor: Theme.of(context).inputDecorationTheme.fillColor,
              counterText: '',
              prefixIcon: Icon(
                Icons.cake_outlined,
                color: Theme.of(context).colorScheme.secondary,
                size: 20,
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withOpacity(0.1),
                  width: 1,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(
                  color: Theme.of(context).colorScheme.secondary,
                  width: 1.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Gender toggle
          Row(
            children: [
              Expanded(
                child: _SelectButton(
                  label: 'Boy 👦',
                  value: 'male',
                  selected: _selectedGender == 'male',
                  onTap: () => setState(() => _selectedGender = 'male'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SelectButton(
                  label: 'Girl 👧',
                  value: 'female',
                  selected: _selectedGender == 'female',
                  onTap: () => setState(() => _selectedGender = 'female'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Active model (fixed)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Theme.of(context).inputDecorationTheme.fillColor,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: Text(
              'Model: Gemini 2.5 Flash',
              style: GoogleFonts.outfit(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.85),
              ),
            ),
          ),

          // Error message
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 12),
            ),
          ],

          const SizedBox(height: 20),

          // CTA button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _startChat,
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.primary,
                foregroundColor: Colors.white,
                disabledBackgroundColor: Theme.of(
                  context,
                ).colorScheme.primary.withOpacity(0.4),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                elevation: 0,
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
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

/// Styled selector button.
class _SelectButton extends StatelessWidget {
  final String label;
  final String value;
  final bool selected;
  final VoidCallback onTap;

  const _SelectButton({
    required this.label,
    required this.value,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    final surface = Theme.of(context).colorScheme.surface;
    final onSurface = Theme.of(context).colorScheme.onSurface;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: selected
              ? primary.withOpacity(0.15)
              : surface.withOpacity(0.6),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? primary : onSurface.withOpacity(0.1),
            width: selected ? 1.5 : 1,
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: GoogleFonts.outfit(
            fontSize: 14,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            color: selected ? primary : onSurface.withOpacity(0.7),
          ),
        ),
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
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: Theme.of(context).colorScheme.secondary.withOpacity(0.15),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
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
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Row(
                children: [
                  const Text('🏆', style: TextStyle(fontSize: 22)),
                  const SizedBox(width: 10),
                  Text(
                    'Session Feedback',
                    style: GoogleFonts.outfit(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  const Spacer(),
                  GestureDetector(
                    onTap: () => Navigator.of(context).pop(),
                    child: Icon(
                      Icons.close_rounded,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withOpacity(0.6),
                      size: 20,
                    ),
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
                      child: Text(
                        _error!,
                        style: const TextStyle(
                          color: Color(0xFFEF4444),
                          fontSize: 13,
                        ),
                      ),
                    )
                  : _entries == null
                  ? Padding(
                      padding: const EdgeInsets.all(40),
                      child: CircularProgressIndicator(
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                    )
                  : _entries!.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.all(40),
                      child: Text(
                        'No feedback submitted yet.\nBe the first!',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.outfit(
                          color: Theme.of(
                            context,
                          ).colorScheme.onSurface.withOpacity(0.5),
                          fontSize: 14,
                        ),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 16,
                      ),
                      itemCount: _entries!.length,
                      separatorBuilder: (_, __) =>
                          const Divider(color: Color(0x15FFFFFF), height: 1),
                      itemBuilder: (_, i) {
                        final e = _entries![i];
                        final rating = (e['rating'] as num?)?.toInt() ?? 0;
                        final name = e['user_name'] as String? ?? 'Anonymous';
                        final feedback = e['feedback'] as String? ?? '';
                        final modelName = e['model_name'] as String? ?? '—';
                        final totalTokens =
                            (e['total_tokens'] as num?)?.toInt() ?? 0;

                        String shortModel = '—';
                        Color modelColor = Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.3);
                        if (modelName.contains('gemini')) {
                          shortModel = 'Gemini';
                          modelColor = Colors.blue;
                        } else if (modelName.contains('gpt-4o')) {
                          shortModel = 'GPT-4o';
                          modelColor = Colors.green;
                        } else if (modelName.contains('claude')) {
                          shortModel = 'Claude';
                          modelColor = Colors.orange;
                        }

                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
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
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurface
                                        .withValues(alpha: 0.6),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          name,
                                          style: GoogleFonts.outfit(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w600,
                                            color: Theme.of(
                                              context,
                                            ).colorScheme.onSurface,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 6,
                                            vertical: 2,
                                          ),
                                          decoration: BoxDecoration(
                                            color: modelColor.withValues(
                                              alpha: 0.15,
                                            ),
                                            borderRadius: BorderRadius.circular(
                                              8,
                                            ),
                                            border: Border.all(
                                              color: modelColor.withValues(
                                                alpha: 0.5,
                                              ),
                                            ),
                                          ),
                                          child: Text(
                                            shortModel,
                                            style: GoogleFonts.outfit(
                                              fontSize: 10,
                                              fontWeight: FontWeight.w600,
                                              color: modelColor,
                                            ),
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
                                            color: Theme.of(
                                              context,
                                            ).colorScheme.secondary,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ],
                                    ),
                                    if (totalTokens > 0)
                                      Padding(
                                        padding: const EdgeInsets.only(
                                          top: 2,
                                          bottom: 2,
                                        ),
                                        child: Text(
                                          '$totalTokens tokens',
                                          style: GoogleFonts.outfit(
                                            fontSize: 11,
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurface
                                                .withValues(alpha: 0.4),
                                          ),
                                        ),
                                      ),
                                    if (feedback.isNotEmpty) ...[
                                      const SizedBox(height: 4),
                                      Text(
                                        '"$feedback"',
                                        style: GoogleFonts.outfit(
                                          fontSize: 13,
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurface
                                              .withOpacity(0.5),
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
                    foregroundColor: Theme.of(context).colorScheme.primary,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'Close',
                    style: GoogleFonts.outfit(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
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

// ─── PIN Dialog ───────────────────────────────────────────────────────────

class _PinDialog extends StatefulWidget {
  final ApiService api;
  const _PinDialog({required this.api});

  @override
  State<_PinDialog> createState() => _PinDialogState();
}

class _PinDialogState extends State<_PinDialog> {
  final _controller = TextEditingController();
  String? _error;
  bool _loading = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final pin = _controller.text.trim();
    if (pin.isEmpty) {
      setState(() => _error = 'Enter the access code');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Validate by actually calling the endpoint
      await widget.api.getTokenAnalytics(pin);
      if (mounted) Navigator.of(context).pop(pin); // return the validated key
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().contains('403')
              ? 'Incorrect access code'
              : e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 360),
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: Theme.of(context).colorScheme.secondary.withOpacity(0.15),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 40,
              spreadRadius: 0,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('🔬', style: TextStyle(fontSize: 22)),
                const SizedBox(width: 10),
                Text(
                  'Professor Access',
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Enter your 8-digit access code to view analytics.',
              style: GoogleFonts.outfit(
                fontSize: 13,
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _controller,
              obscureText: true,
              maxLength: 8,
              keyboardType: TextInputType.number,
              autofocus: true,
              onSubmitted: (_) => _submit(),
              style: GoogleFonts.outfit(
                color: Theme.of(context).colorScheme.onSurface,
                fontSize: 18,
                letterSpacing: 4,
              ),
              decoration: InputDecoration(
                hintText: '••••••••',
                hintStyle: TextStyle(
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withOpacity(0.3),
                  letterSpacing: 6,
                ),
                filled: true,
                fillColor: Theme.of(context).inputDecorationTheme.fillColor,
                counterText: '',
                prefixIcon: Icon(
                  Icons.lock_outline_rounded,
                  color: Theme.of(context).colorScheme.secondary,
                  size: 20,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withOpacity(0.1),
                    width: 1,
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(
                    color: Theme.of(context).colorScheme.secondary,
                    width: 1.5,
                  ),
                ),
                errorText: _error,
                errorStyle: const TextStyle(
                  color: Color(0xFFEF4444),
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    style: TextButton.styleFrom(
                      foregroundColor: Theme.of(
                        context,
                      ).colorScheme.onSurface.withOpacity(0.6),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Text(
                      'Cancel',
                      style: GoogleFonts.outfit(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _loading ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.primary,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: Theme.of(
                        context,
                      ).colorScheme.primary.withOpacity(0.4),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 0,
                    ),
                    child: _loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : Text(
                            'Unlock 🔬',
                            style: GoogleFonts.outfit(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
