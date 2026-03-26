import 'package:flutter/material.dart';
import 'package:clothie_web/models/chat_message.dart';
import 'package:clothie_web/widgets/thinking_indicator.dart';
import 'package:clothie_web/widgets/product_card.dart';
import 'package:clothie_web/config.dart';

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

                      // Message text
                      if (message.content.isNotEmpty)
                        Text(
                          message.content,
                          style: const TextStyle(
                            color: Color(kTextPrimary),
                            fontSize: 14,
                            height: 1.6,
                          ),
                        ),

                      // Streaming cursor
                      if (isStreaming)
                        _BlinkingCursor(),

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

                // Products below the bubble
                if (message.products.isNotEmpty)
                  ProductCardList(products: message.products),
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
