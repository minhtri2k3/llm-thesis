import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:clothie_web/config.dart';
import 'package:clothie_web/providers/chat_provider.dart';
import 'package:clothie_web/widgets/chat_bubble.dart';
import 'package:clothie_web/screens/rating_screen.dart';

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

  void _endSession() {
    Navigator.of(context).push(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 400),
        pageBuilder: (_, anim, __) => RatingScreen(
          sessionId: widget.sessionId,
          userName: widget.userName,
        ),
        transitionsBuilder: (_, anim, __, child) =>
            FadeTransition(opacity: anim, child: child),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // ChatProvider is injected at the app level (main.dart)
    return ChangeNotifierProvider(
      create: (_) => ChatProvider(),
      child: Consumer<ChatProvider>(
        builder: (context, provider, _) {
          // Scroll to bottom whenever messages change
          if (provider.messages.isNotEmpty) _scrollToBottom();

          return Scaffold(
            backgroundColor: const Color(kBgColor),
            appBar: _buildAppBar(),
            body: Column(
              children: [
                // Message list
                Expanded(
                  child: provider.messages.isEmpty
                      ? _buildEmptyState()
                      : _buildMessageList(provider),
                ),

                // Error banner
                if (provider.error != null)
                  _buildErrorBanner(provider),

                // Input row
                _buildInputRow(provider),
              ],
            ),
          );
        },
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(kSurfaceColor),
      elevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 16,
      title: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: const Color(kAccentColor),
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
                  color: const Color(kTextPrimary),
                ),
              ),
              Text(
                'Hi ${widget.userName} 👋',
                style: GoogleFonts.outfit(
                  fontSize: 11,
                  color: const Color(kAccentLight),
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: OutlinedButton(
            onPressed: _endSession,
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(kAccentLight),
              side: const BorderSide(color: Color(kAccentLight), width: 1),
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
            height: 1,
            color: Colors.white.withOpacity(0.06)),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('👗', style: const TextStyle(fontSize: 60)),
          const SizedBox(height: 16),
          Text(
            'Ask me about fashion!',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: const Color(kTextPrimary),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Outfit ideas, color matching, style tips — I\'ve got you.',
            style: GoogleFonts.outfit(
              fontSize: 14,
              color: const Color(kTextSecondary),
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

  Widget _buildErrorBanner(ChatProvider provider) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF7F1D1D).withOpacity(0.6),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFEF4444).withOpacity(0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              provider.error!,
              style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 12),
            ),
          ),
          GestureDetector(
            onTap: provider.clearError,
            child: const Icon(Icons.close, color: Color(0xFFFCA5A5), size: 16),
          ),
        ],
      ),
    );
  }

  Widget _buildInputRow(ChatProvider provider) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      decoration: BoxDecoration(
        color: const Color(kSurfaceColor),
        border: Border(
          top: BorderSide(color: Colors.white.withOpacity(0.06)),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _inputController,
              onSubmitted: (_) => _sendMessage(provider),
              style: GoogleFonts.outfit(
                  color: const Color(kTextPrimary), fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Ask about fashion...',
                hintStyle: TextStyle(
                    color: const Color(kTextSecondary).withOpacity(0.7),
                    fontSize: 14),
                filled: true,
                fillColor: const Color(kCardColor),
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 12),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(
                      color: Colors.white.withOpacity(0.08)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(
                      color: Color(kAccentLight), width: 1.5),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          _SendButton(
            isLoading: provider.isLoading,
            onTap: () => _sendMessage(provider),
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
                ? const Color(kAccentColor).withOpacity(0.4)
                : _hovered
                    ? const Color(kAccentLight)
                    : const Color(kAccentColor),
            borderRadius: BorderRadius.circular(14),
          ),
          child: widget.isLoading
              ? const Center(
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  ),
                )
              : const Icon(Icons.send_rounded, color: Colors.white, size: 20),
        ),
      ),
    );
  }
}
