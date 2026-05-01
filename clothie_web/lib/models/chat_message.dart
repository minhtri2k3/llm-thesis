import 'package:flutter/foundation.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/models/product.dart';

enum MessageRole { user, assistant }

enum MessageStatus { done, streaming, thinking }

class ThinkingStep {
  final String text;
  ThinkingStep(this.text);
}

class ChatMessage {
  final String id;
  final MessageRole role;
  String content;
  MessageStatus status;
  List<ThinkingStep> thinkingSteps;
  List<Product> products;

  /// Items from a selection_confirm SSE — rendered as a confirm-card strip.
  List<CartItem> confirmItems;
  String? stylingTip;

  /// Set to true when an offer_prompt SSE is received — triggers the offer dialog in ChatScreen.
  bool showOfferDialog;

  /// True only when the backend has emitted the 'search' thinking step.
  /// Used to show the shimmer skeleton during active product searching.
  bool isSearching;

  /// Image bytes for PATH 2 (image search). Rendered as thumbnail in chat.
  Uint8List? imageBytes;

  /// Image filename for display (e.g., "test01.png")
  String? imageFileName;

  ChatMessage({
    required this.id,
    required this.role,
    this.content = '',
    this.status = MessageStatus.done,
    List<ThinkingStep>? thinkingSteps,
    List<Product>? products,
    List<CartItem>? confirmItems,
    this.stylingTip,
    this.showOfferDialog = false,
    this.imageBytes,
    this.imageFileName,
  })  : thinkingSteps = thinkingSteps ?? [],
        products = products ?? [],
        confirmItems = confirmItems ?? [],
        isSearching = false;

  factory ChatMessage.user(String text) => ChatMessage(
        id: DateTime.now().microsecondsSinceEpoch.toString(),
        role: MessageRole.user,
        content: text,
        status: MessageStatus.done,
      );

  factory ChatMessage.assistantPending() => ChatMessage(
        id: '${DateTime.now().microsecondsSinceEpoch}_ai',
        role: MessageRole.assistant,
        content: '',
        status: MessageStatus.thinking,
      );
}
