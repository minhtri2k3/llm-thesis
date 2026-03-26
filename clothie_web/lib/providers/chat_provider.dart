import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/models/chat_message.dart';
import 'package:clothie_web/models/product.dart';
import 'package:clothie_web/services/api_service.dart';

/// Manages chat state for a single session.
///
/// Exposes [messages], [isLoading], and methods to send messages and reset.
/// Consumed via [ChangeNotifierProvider] in the widget tree.
class ChatProvider extends ChangeNotifier {
  final ApiService _api;

  /// Called when the agent confirms items were saved to the DB.
  /// Passes the list of newly confirmed [CartItem]s to the cart.
  final void Function(List<CartItem>)? onItemsSaved;

  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _error;

  ChatProvider({ApiService? api, this.onItemsSaved})
      : _api = api ?? ApiService();

  /// Allows [ChatScreen] to update the callback when [CartProvider] changes.
  void updateCallback(void Function(List<CartItem>) callback) {
    // no-op if already set and unchanged; called by ProxyProvider
  }

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Sends [userText] to the AI and streams the response.
  ///
  /// Handles all SSE event types and updates the pending AI message
  /// in place as tokens arrive, triggering [notifyListeners] on each update.
  Future<void> sendMessage(String userText, String sessionId) async {
    if (_isLoading) return;

    _error = null;
    _messages.add(ChatMessage.user(userText));
    final aiMsg = ChatMessage.assistantPending();
    _messages.add(aiMsg);
    _isLoading = true;
    notifyListeners();

    try {
      await for (final event in _api.chatStream(userText, sessionId)) {
        _handleSseEvent(event, aiMsg);
        notifyListeners();
      }
    } catch (e) {
      aiMsg.content = 'Sorry, something went wrong. Please try again.';
      aiMsg.status = MessageStatus.done;
      _error = e.toString();
    } finally {
      // Ensure status is finalized even if stream ends without `done` event
      if (aiMsg.status != MessageStatus.done) {
        aiMsg.status = MessageStatus.done;
      }
      _isLoading = false;
      notifyListeners();
    }
  }

  void _handleSseEvent(SseEvent event, ChatMessage aiMsg) {
    final data = event.data;
    switch (event.type) {
      case 'thinking_start':
        aiMsg.status = MessageStatus.thinking;

      case 'thinking_step':
        final text = data is Map ? (data['step'] as String? ?? '') : data.toString();
        if (text.isNotEmpty) {
          aiMsg.thinkingSteps.add(ThinkingStep(text));
        }

      case 'thinking_end':
        // Keep thinking steps visible but switch to streaming mode
        aiMsg.status = MessageStatus.streaming;

      case 'token':
        aiMsg.status = MessageStatus.streaming;
        final token = data is Map
            ? (data['text'] as String? ?? '')
            : data.toString();
        aiMsg.content += token;

      case 'clarification':
        aiMsg.status = MessageStatus.streaming;
        final text = data is Map
            ? (data['text'] as String? ?? '')
            : data.toString();
        aiMsg.content += text;

      case 'products':
        final rawList = data is Map
            ? (data['products'] as List? ?? [])
            : (data as List? ?? []);
        aiMsg.products = rawList
            .whereType<Map<String, dynamic>>()
            .map(Product.fromJson)
            .toList();

      // ── Selection flow events ──────────────────────────────────────────
      case 'selection_confirm':
        // Agent shows the confirmation preview (selected items + yes/no prompt)
        final text = data is Map ? (data['text'] as String? ?? '') : data.toString();
        if (text.isNotEmpty) aiMsg.content = text;
        aiMsg.status = MessageStatus.done;

      case 'selection_saved':
        // Items confirmed and saved to DB; notify CartProvider
        final text = data is Map ? (data['text'] as String? ?? '') : data.toString();
        if (text.isNotEmpty) aiMsg.content = text;
        if (data is Map) {
          final rawItems = data['items'] as List?;
          if (rawItems != null && onItemsSaved != null) {
            final cartItems = rawItems
                .whereType<Map<String, dynamic>>()
                .map(CartItem.fromAgentJson)
                .toList();
            onItemsSaved!(cartItems);
          }
        }
        aiMsg.status = MessageStatus.done;

      case 'selection_cancelled':
        final text = data is Map ? (data['text'] as String? ?? '') : data.toString();
        if (text.isNotEmpty) aiMsg.content = text;
        aiMsg.status = MessageStatus.done;

      case 'selections_list':
        final text = data is Map ? (data['text'] as String? ?? '') : data.toString();
        if (text.isNotEmpty) aiMsg.content = text;
        aiMsg.status = MessageStatus.done;

      case 'done':
        if (data is Map) {
          final tip = data['styling_tip'] as String?;
          if (tip != null && tip.isNotEmpty) {
            aiMsg.stylingTip = tip;
          }
        }
        aiMsg.status = MessageStatus.done;

      case 'error':
        final msg = data is Map
            ? (data['message'] as String? ?? 'Unknown error')
            : data.toString();
        aiMsg.content = 'Error: $msg';
        aiMsg.status = MessageStatus.done;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Resets chat state for a new session (e.g., after returning to splash).
  void reset() {
    _messages.clear();
    _isLoading = false;
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
