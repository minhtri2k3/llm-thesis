import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:clothie_web/extension/config.dart';
import 'package:clothie_web/extension/theme_provider.dart';
import 'package:clothie_web/screens/cart/cart_provider.dart';
import 'package:clothie_web/screens/chat/chat_provider.dart';
import 'package:clothie_web/screens/cart/cart_screen.dart';
import 'package:clothie_web/screens/rating_screen.dart';
import 'package:clothie_web/widgets/chat_bubble.dart';
import 'package:clothie_web/widgets/flying_icon_bg.dart';
import 'package:clothie_web/models/product.dart';

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
  int _lastMessageCount = 0;
  bool _offerDialogShown = false;

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

  /// Show user a warning if image is large (>3MB).
  void _warnIfLargeImage(int sizeInBytes) {
    final sizeInMB = sizeInBytes / 1024 / 1024;
    if (sizeInMB > 3.0) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('📸 Large image (${sizeInMB.toStringAsFixed(1)}MB). Upload may take longer.'),
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  Future<void> _searchByImage(ChatProvider provider) async {
    if (provider.isLoading) return;

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['png'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    final fileName = file.name;
    if (!fileName.toLowerCase().endsWith('.png')) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Only .png files are supported.')),
      );
      return;
    }

    var bytes = file.bytes;
    if (bytes == null || bytes.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to read selected image file.')),
      );
      return;
    }

    // Warn if image is large but allow it
    _warnIfLargeImage(bytes.lengthInBytes);

    await provider.searchByImage(bytes, fileName, widget.sessionId);
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
          update: (ctx, cart, prev) =>
              prev!..updateCallback(cart.onSelectionSaved),
        ),
      ],
      child: Builder(
        builder: (context) {
          final provider = context.watch<ChatProvider>();
          if (provider.messages.isNotEmpty) _scrollToBottom();

          // Reset offer dialog flag when a new search cycle starts (messages grow)
          if (provider.messages.length != _lastMessageCount) {
            _lastMessageCount = provider.messages.length;
            _offerDialogShown = false;
          }

          // ── Offer prompt: trigger dialog after successful search ───────────
          final lastMsg = provider.messages.isNotEmpty
              ? provider.messages.last
              : null;
          if (lastMsg != null &&
              lastMsg.showOfferDialog &&
              !_offerDialogShown) {
            _offerDialogShown = true;
            final offerProducts = lastMsg.products; // same list shown in chat
            WidgetsBinding.instance.addPostFrameCallback(
              (_) => _showOfferDialog(context, provider, offerProducts),
            );
          }

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
                    if (provider.error != null) _buildErrorBanner(provider),
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
              border: Border.all(
                color: Theme.of(context).colorScheme.primary,
                width: 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: Theme.of(
                    context,
                  ).colorScheme.primary.withOpacity(0.25),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                const Text('\u{1F6CD}\uFE0F', style: TextStyle(fontSize: 20)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Added to your cart 🛍️',
                        style: GoogleFonts.outfit(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Check the top‑right corner to see all your picks!',
                        style: GoogleFonts.outfit(
                          color: Theme.of(
                            context,
                          ).colorScheme.onPrimaryContainer.withOpacity(0.7),
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
                    Icon(
                      Icons.north_east_rounded,
                      color: Theme.of(context).colorScheme.primary,
                      size: 18,
                    ),
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
                'Hi ${widget.userName} 👋',
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
        // ── Cart icon with badge ──────────────────────────────────────────
        Consumer<CartProvider>(
          builder: (ctx, cart, _) => IconButton(
            tooltip: 'My selections',
            onPressed: () async {
              final orderPlaced = await CartScreen.show(
                ctx,
                widget.sessionId,
                widget.userName,
              );
              if (orderPlaced == true && ctx.mounted) {
                _showRatingDialog(ctx);
              }
            },
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(
                  Icons.shopping_bag_outlined,
                  color: Theme.of(context).colorScheme.onSurface,
                  size: 24,
                ),
                if (cart.count > 0)
                  Positioned(
                    top: -4,
                    right: -6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 5,
                        vertical: 1,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primary,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: Theme.of(context).colorScheme.surface,
                          width: 1.5,
                        ),
                      ),
                      child: Text(
                        '${cart.count}',
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
              side: BorderSide(
                color: Theme.of(context).colorScheme.primary,
                width: 1,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            ),
            child: Text('End Session', style: GoogleFonts.outfit(fontSize: 13)),
          ),
        ),
      ],
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(1),
        child: Container(
          height: 1,
          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.06),
        ),
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
      itemBuilder: (_, i) => ChatBubble(
        message: provider.messages[i],
        sessionId: widget.sessionId,
      ),
    );
  }

  Widget _buildInputRow(BuildContext context, ChatProvider provider) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.06),
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: CallbackShortcuts(
              bindings: <ShortcutActivator, VoidCallback>{
                // Shift+Enter inserts a newline at cursor position
                const SingleActivator(
                  LogicalKeyboardKey.enter,
                  shift: true,
                ): () {
                  final ctrl = _inputController;
                  final text = ctrl.text;
                  final sel = ctrl.selection;
                  final before = text.substring(
                    0,
                    sel.start < 0 ? 0 : sel.start,
                  );
                  final after = text.substring(sel.end < 0 ? 0 : sel.end);
                  ctrl.value = TextEditingValue(
                    text: '$before\n$after',
                    selection: TextSelection.collapsed(
                      offset: before.length + 1,
                    ),
                  );
                },
                // Plain Enter sends (convenience on desktop)
                const SingleActivator(LogicalKeyboardKey.enter): () =>
                    _sendMessage(context.read<ChatProvider>()),
              },
              child: TextField(
                controller: _inputController,
                maxLines: null,
                keyboardType: TextInputType.multiline,
                textInputAction: TextInputAction.newline,
                onSubmitted: null, // handled by CallbackShortcuts above
                style: GoogleFonts.outfit(
                  color: Theme.of(context).colorScheme.onSurface,
                  fontSize: 14,
                ),
                decoration: InputDecoration(
                  hintText: 'Ask about fashion...',
                  hintStyle: TextStyle(
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withOpacity(0.5),
                    fontSize: 14,
                  ),
                  filled: true,
                  fillColor: Theme.of(context).inputDecorationTheme.fillColor,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withOpacity(0.08),
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(
                      color: Theme.of(context).colorScheme.primary,
                      width: 1.5,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          if (kEnablePath2ImageSearch) ...[
            Tooltip(
              message: 'Search by image (PNG)',
              child: IconButton(
                onPressed: provider.isLoading
                    ? null
                    : () => _searchByImage(context.read<ChatProvider>()),
                icon: Icon(
                  Icons.image_search_rounded,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
            ),
            const SizedBox(width: 4),
          ],
          _SendButton(
            isLoading: provider.isLoading,
            onTap: () => _sendMessage(context.read<ChatProvider>()),
          ),
        ],
      ),
    );
  }

  /// Shows the rating dialog; on submit navigates back to [RegisterScreen].
  void _showRatingDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => RatingDialog(
        sessionId: widget.sessionId,
        userName: widget.userName,
        onComplete: () {
          context.goNamed('register');
        },
      ),
    );
  }

  /// Shows the offer dialog after a successful product search.
  void _showOfferDialog(
    BuildContext context,
    ChatProvider provider,
    List<Product> products,
  ) {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '\u{1F6CD}\uFE0F Ready to order?',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 14),
              // Product thumbnail strip
              if (products.isNotEmpty)
                SizedBox(
                  height: 100,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 8),
                    itemBuilder: (_, i) {
                      final p = products[i];
                      return Column(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.network(
                              p.imageUrl,
                              width: 64,
                              height: 72,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => Container(
                                width: 64,
                                height: 72,
                                color: Theme.of(
                                  context,
                                ).colorScheme.surfaceContainerHighest,
                                child: const Icon(Icons.checkroom),
                              ),
                            ),
                          ),
                          const SizedBox(height: 4),
                          SizedBox(
                            width: 64,
                            child: Text(
                              p.label,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.outfit(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              const SizedBox(height: 14),
              Text(
                'Would you like to place an order for these items, or continue looking?',
                style: GoogleFonts.outfit(fontSize: 13, height: 1.5),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      provider.sendMessage(
                        '__offer_declined__',
                        widget.sessionId,
                      );
                    },
                    child: const Text('Keep browsing'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.icon(
                    onPressed: () async {
                      Navigator.pop(ctx);
                      final placed = await CartScreen.show(
                        context,
                        widget.sessionId,
                        widget.userName,
                      );
                      if (placed == true && context.mounted) {
                        _showRatingDialog(context);
                      }
                    },
                    icon: const Icon(Icons.shopping_cart_rounded, size: 16),
                    label: const Text('Order now'),
                  ),
                ],
              ),
            ],
          ),
        ),
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
        border: Border.all(
          color: Theme.of(context).colorScheme.error.withOpacity(0.5),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.error_outline,
            color: Theme.of(context).colorScheme.error,
            size: 16,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              provider.error!,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onErrorContainer,
                fontSize: 12,
              ),
            ),
          ),
          GestureDetector(
            onTap: provider.clearError,
            child: Icon(
              Icons.close,
              color: Theme.of(context).colorScheme.onErrorContainer,
              size: 16,
            ),
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
                      strokeWidth: 2,
                      color: Theme.of(context).colorScheme.onPrimary,
                    ),
                  ),
                )
              : Icon(
                  Icons.send_rounded,
                  color: Theme.of(context).colorScheme.onPrimary,
                  size: 20,
                ),
        ),
      ),
    );
  }
}
