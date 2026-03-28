import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:clothie_web/providers/theme_provider.dart';
import 'package:clothie_web/providers/cart_provider.dart';
import 'package:clothie_web/providers/chat_provider.dart';
import 'package:clothie_web/screens/cart_screen.dart';
import 'package:clothie_web/screens/rating_screen.dart';
import 'package:clothie_web/screens/splash_screen.dart';
import 'package:clothie_web/widgets/chat_bubble.dart';
import 'package:clothie_web/widgets/flying_icon_bg.dart';

class ChatScreen extends StatefulWidget {
  final String sessionId;
  final String userName;

  const ChatScreen({
    super.key,
    required this.sessionId,
    required this.userName,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();

  // ── Top-banner notification state ──────────────────────────────
  bool _showTopBanner = false;

  void _showBanner() {
    if (!mounted) return;
    setState(() => _showTopBanner = true);
    Future.delayed(const Duration(seconds: 5), () {
      if (mounted) setState(() => _showTopBanner = false);
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(ChatProvider provider) async {
    final text = _inputController.text.trim();
    if (text.isEmpty || provider.isLoading) return;
    _inputController.clear();
    await provider.sendMessage(text, widget.sessionId);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<CartProvider>(
          create: (_) => CartProvider(sessionId: widget.sessionId),
        ),
        ChangeNotifierProxyProvider<CartProvider, ChatProvider>(
          create: (ctx) => ChatProvider(
            onSelectionSaved: ctx.read<CartProvider>().onSelectionSaved,
          ),
          update: (ctx, cart, prev) => prev!
            ..updateCallback(cart.onSelectionSaved),
        ),
      ],
      child: Builder(
        builder: (context) {
          final provider = context.watch<ChatProvider>();
          if (provider.messages.isNotEmpty) _scrollToBottom();

          // ── Cart save: trigger top banner ─────────────────────────────
          if (provider.pendingCartNotification) {
            provider.clearCartNotification();
            WidgetsBinding.instance.addPostFrameCallback((_) => _showBanner());
          }

          return Scaffold(
            backgroundColor: Theme.of(context).scaffoldBackgroundColor,
            appBar: _buildAppBar(context),
            body: Stack(
              children: [
                // Animated background (same as splash & register)
                const Positioned.fill(
                  child: FlyingIconBackground(iconCount: 10),
                ),
                // ── Top notification banner ──────────────────────
                AnimatedSlide(
                  offset: _showTopBanner ? Offset.zero : const Offset(0, -1),
                  duration: const Duration(milliseconds: 350),
                  curve: Curves.easeOutCubic,
                  child: AnimatedOpacity(
                    opacity: _showTopBanner ? 1.0 : 0.0,
                    duration: const Duration(milliseconds: 300),
                    child: _buildTopBanner(),
                  ),
                ),
                Column(
                  children: [
                    Expanded(
                      child: provider.messages.isEmpty
                          ? _buildEmptyState()
                          : _buildMessageList(provider),
                    ),
                    if (provider.error != null)
                      _buildErrorBanner(provider),
                    _buildInputRow(context, provider),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// Floating banner that appears at the top of the chat body under the AppBar.
  Widget _buildTopBanner() {
    return Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        child: Material(
          color: Colors.transparent,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Theme.of(context).colorScheme.primary, width: 1),
              boxShadow: [
                BoxShadow(
                  color: Theme.of(context).colorScheme.primary.withOpacity(0.25),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                const Text('\u{1F6CD}\uFE0F',
                    style: TextStyle(fontSize: 20)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Item saved! \u2728',
                        style: GoogleFonts.outfit(
                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Whenever you want to end, press the button and vote for me. Love you \u{1F495}',
                        style: GoogleFonts.outfit(
                          color: Theme.of(context).colorScheme.onPrimaryContainer.withOpacity(0.7),
                          fontSize: 11,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.north_east_rounded,
                        color: Theme.of(context).colorScheme.primary, size: 18),
                    Text(
                      'End',
                      style: GoogleFonts.outfit(
                        color: Theme.of(context).colorScheme.primary,
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return AppBar(
      backgroundColor: Theme.of(context).colorScheme.surface,
      elevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 16,
      title: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Center(
              child: Text('👗', style: TextStyle(fontSize: 18)),
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Clothie',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
              Text(
                'Hi \${widget.userName} 👋',
                style: GoogleFonts.outfit(
                  fontSize: 11,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        // ── Theme toggle ───────────────────────────────────────────────────
        Consumer<ThemeProvider>(
          builder: (context, themeProvider, child) {
            return IconButton(
              icon: Icon(themeProvider.isDarkMode ? Icons.light_mode_rounded : Icons.dark_mode_rounded),
              color: Theme.of(context).colorScheme.onSurface,
              onPressed: () {
                themeProvider.toggleTheme();
              },
            );
          },
        ),
        // ── Cart icon with badge ──────────────────────────────────────────
        Consumer<CartProvider>(
          builder: (ctx, cart, _) => IconButton(
            tooltip: 'My selections',
            onPressed: () => CartScreen.show(ctx),
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(Icons.shopping_bag_outlined,
                    color: Theme.of(context).colorScheme.onSurface, size: 24),
                if (cart.count > 0)
                  Positioned(
                    top: -4,
                    right: -6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primary,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                            color: Theme.of(context).colorScheme.surface, width: 1.5),
                      ),
                      child: Text(
                        '\${cart.count}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onPrimary,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),
        // ── End Session ───────────────────────────────────────────────────
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: OutlinedButton(
            onPressed: () => _showRatingDialog(context),
            style: OutlinedButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.primary,
              side: BorderSide(color: Theme.of(context).colorScheme.primary, width: 1),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            ),
            child: Text('End Session',
                style: GoogleFonts.outfit(fontSize: 13)),
          ),
        ),
      ],
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(1),
        child: Container(
            height: 1, color: Theme.of(context).colorScheme.onSurface.withOpacity(0.06)),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('👗', style: TextStyle(fontSize: 60)),
          const SizedBox(height: 16),
          Text(
            'Ask me about fashion!',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Outfit ideas, color matching, style tips — I\'ve got you.',
            style: GoogleFonts.outfit(
              fontSize: 14,
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildMessageList(ChatProvider provider) {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      itemCount: provider.messages.length,
      itemBuilder: (_, i) => ChatBubble(message: provider.messages[i]),
    );
  }

  Widget _buildInputRow(BuildContext context, ChatProvider provider) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.06)),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _inputController,
              onSubmitted: (_) => _sendMessage(context.read<ChatProvider>()),
              style: GoogleFonts.outfit(
                  color: Theme.of(context).colorScheme.onSurface, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Ask about fashion...',
                hintStyle: TextStyle(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                    fontSize: 14),
                filled: true,
                fillColor: Theme.of(context).inputDecorationTheme.fillColor,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.08)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(
                      color: Theme.of(context).colorScheme.primary, width: 1.5),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          _SendButton(
            isLoading: provider.isLoading,
            onTap: () => _sendMessage(context.read<ChatProvider>()),
          ),
        ],
      ),
    );
  }

  /// Shows the rating dialog; on submit navigates back to [SplashScreen].
  void _showRatingDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => RatingDialog(
        sessionId: widget.sessionId,
        userName: widget.userName,
        onComplete: () {
          Navigator.of(context).pushAndRemoveUntil(
            PageRouteBuilder(
              transitionDuration: const Duration(milliseconds: 600),
              pageBuilder: (_, anim, __) => const SplashScreen(),
              transitionsBuilder: (_, anim, __, child) =>
                  FadeTransition(opacity: anim, child: child),
            ),
            (_) => false,
          );
        },
      ),
    );
  }

  Widget _buildErrorBanner(ChatProvider provider) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Theme.of(context).colorScheme.error.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              provider.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer, fontSize: 12),
            ),
          ),
          GestureDetector(
            onTap: provider.clearError,
            child: Icon(Icons.close, color: Theme.of(context).colorScheme.onErrorContainer, size: 16),
          ),
        ],
      ),
    );
  }
}

class _SendButton extends StatefulWidget {
  final bool isLoading;
  final VoidCallback onTap;
  const _SendButton({required this.isLoading, required this.onTap});

  @override
  State<_SendButton> createState() => _SendButtonState();
}

class _SendButtonState extends State<_SendButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.isLoading ? null : widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: widget.isLoading
                ? Theme.of(context).colorScheme.primary.withOpacity(0.4)
                : _hovered
                    ? Theme.of(context).colorScheme.primary.withOpacity(0.8)
                    : Theme.of(context).colorScheme.primary,
            borderRadius: BorderRadius.circular(14),
          ),
          child: widget.isLoading
              ? Center(
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Theme.of(context).colorScheme.onPrimary),
                  ),
                )
              : Icon(Icons.send_rounded, color: Theme.of(context).colorScheme.onPrimary, size: 20),
        ),
      ),
    );
  }
}
