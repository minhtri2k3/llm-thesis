import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:clothie_web/config.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/models/chat_message.dart';
import 'package:clothie_web/widgets/product_card.dart';
import 'package:clothie_web/widgets/thinking_indicator.dart';


class ChatBubble extends StatelessWidget {
  final ChatMessage message;
  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return message.role == MessageRole.user
        ? _UserBubble(message: message)
        : _AssistantBubble(message: message);
  }
}

// ── Inline Markdown renderer ────────────────────────────────────────────────
/// Renders text with simple inline markdown:
/// - **bold** → accent-coloured bold (asterisks hidden)
/// - *italic* → italic (asterisks hidden)
/// - plain text → default body style
class _MarkdownText extends StatelessWidget {
  final String text;
  const _MarkdownText({required this.text});

  // Matches **...** before *...* to handle nesting correctly
  static final _boldRe = RegExp(r'\*\*(.+?)\*\*');
  static final _italicRe = RegExp(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)');

  List<InlineSpan> _parse(String input) {
    final spans = <InlineSpan>[];
    int cursor = 0;

    while (cursor < input.length) {
      final boldMatch = _boldRe.firstMatch(input.substring(cursor));
      final italicMatch = _italicRe.firstMatch(input.substring(cursor));

      Match? match;
      bool isBold = false;
      if (boldMatch != null &&
          (italicMatch == null || boldMatch.start <= italicMatch.start)) {
        match = boldMatch;
        isBold = true;
      } else if (italicMatch != null) {
        match = italicMatch;
      }

      if (match == null) {
        spans.add(TextSpan(text: input.substring(cursor)));
        break;
      }

      if (match.start > 0) {
        spans.add(
            TextSpan(text: input.substring(cursor, cursor + match.start)));
      }

      spans.add(TextSpan(
        text: match.group(1),
        style: TextStyle(
          color: isBold ? const Color(kAccentLight) : null,
          fontWeight: isBold ? FontWeight.w700 : null,
          fontStyle: isBold ? null : FontStyle.italic,
        ),
      ));

      cursor += match.end;
    }

    return spans;
  }

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        style: GoogleFonts.outfit(
          color: const Color(kTextPrimary),
          fontSize: 14,
          height: 1.6,
        ),
        children: _parse(text),
      ),
    );
  }
}
/// User message — right-aligned, violet gradient
class _UserBubble extends StatelessWidget {
  final ChatMessage message;
  const _UserBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 60),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF7C3AED), Color(0xFF4C1D95)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(18),
                  topRight: Radius.circular(18),
                  bottomLeft: Radius.circular(18),
                  bottomRight: Radius.circular(4),
                ),
                boxShadow: [
                  BoxShadow(
                    color: const Color(kAccentColor).withOpacity(0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Text(
                message.content,
                style: const TextStyle(
                  color: Color(kTextPrimary),
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Assistant message — left-aligned with thinking indicator + products
class _AssistantBubble extends StatelessWidget {
  final ChatMessage message;
  const _AssistantBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isThinking = message.status == MessageStatus.thinking;
    final isStreaming = message.status == MessageStatus.streaming;
    final isDone = message.status == MessageStatus.done;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16, right: 60),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Avatar
          Container(
            width: 32,
            height: 32,
            margin: const EdgeInsets.only(right: 10, top: 2),
            decoration: BoxDecoration(
              color: const Color(kAccentColor),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Center(child: Text('👗', style: TextStyle(fontSize: 16))),
          ),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: const Color(kCardColor),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(4),
                      topRight: Radius.circular(18),
                      bottomLeft: Radius.circular(18),
                      bottomRight: Radius.circular(18),
                    ),
                    border: Border.all(
                        color: Colors.white.withOpacity(0.06), width: 1),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Thinking indicator
                      if (isThinking || message.thinkingSteps.isNotEmpty) ...[
                        ThinkingIndicator(
                          steps: message.thinkingSteps,
                          isDone: isDone || isStreaming,
                        ),
                        if (message.content.isNotEmpty)
                          const SizedBox(height: 8),
                      ],

                      // Message text — renders **bold** as coloured spans
                      if (message.content.isNotEmpty)
                        _MarkdownText(text: message.content),

                      // Streaming cursor
                      if (isStreaming)
                        _BlinkingCursor(),

                      // ── Product images inline (like Gradio) ──────────
                      if (message.products.isNotEmpty && !isThinking) ...[
                        const SizedBox(height: 12),
                        const Divider(color: Color(0x22FFFFFF), height: 1),
                        const SizedBox(height: 10),
                        const Text(
                          '🛍️ Found items:',
                          style: TextStyle(
                            color: Color(kAccentLight),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.3,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ProductCardList(products: message.products),
                      ],

                      // ── Confirm items strip (images from selection_confirm)
                      if (message.confirmItems.isNotEmpty && !isThinking) ...[
                        const SizedBox(height: 12),
                        const Divider(color: Color(0x22FFFFFF), height: 1),
                        const SizedBox(height: 10),
                        const Text(
                          '✅ Selected items:',
                          style: TextStyle(
                            color: Color(kAccentLight),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.3,
                          ),
                        ),
                        const SizedBox(height: 8),
                        _ConfirmItemStrip(items: message.confirmItems),
                      ],

                      // Styling tip (italic footer)
                      if (message.stylingTip != null &&
                          message.stylingTip!.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(
                          '✨ ${message.stylingTip}',
                          style: const TextStyle(
                            color: Color(kAccentLight),
                            fontSize: 12,
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
          ),
        ],
      ),
    );
  }
}

/// Blinking cursor effect during streaming
class _BlinkingCursor extends StatefulWidget {
  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    )..repeat(reverse: true);
    _opacity = Tween(begin: 0.0, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: const Text('▌',
          style: TextStyle(color: Color(kAccentLight), fontSize: 14)),
    );
  }
}

/// Horizontal strip of confirm-item images shown inside a `selection_confirm`
/// bubble. Images are fetched via the full API URL stored in [CartItem.imageUrl].
class _ConfirmItemStrip extends StatelessWidget {
  final List<CartItem> items;
  const _ConfirmItemStrip({required this.items});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 140,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final item = items[i];
          return Container(
            width: 110,
            decoration: BoxDecoration(
              color: const Color(kCardColor),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: const Color(kAccentLight).withOpacity(0.3), width: 1),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Image.network(
                      item.imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: const Color(kSurfaceColor),
                        child: const Icon(Icons.checkroom,
                            color: Color(kAccentLight), size: 32),
                      ),
                    ),
                  ),
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Text(
                      item.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: Color(kTextPrimary),
                          fontSize: 10,
                          fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
