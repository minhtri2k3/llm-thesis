import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:clothie_web/config.dart';
import 'package:clothie_web/models/cart_item.dart';

/// Represents a single SSE event from the backend.
class SseEvent {
  final String type;
  final dynamic data;
  const SseEvent({required this.type, required this.data});
}

class ApiService {
  final http.Client _client;

  ApiService({http.Client? client}) : _client = client ?? http.Client();

  /// Creates a new session and returns the session_id.
  Future<String> createSession(String userName) async {
    final uri = Uri.parse('$kApiBaseUrl/api/sessions');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'user_name': userName}),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to create session: ${response.body}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return json['session_id'] as String;
  }

  /// Streams SSE events from the chat endpoint.
  ///
  /// Uses POST (not GET) because the backend expects message + session_id.
  /// Flutter Web cannot use native EventSource for POST, so we use
  /// http.StreamedRequest and parse the SSE text protocol manually.
  Stream<SseEvent> chatStream(String message, String sessionId) async* {
    final uri = Uri.parse('$kApiBaseUrl/api/chat/stream');

    final request = http.Request('POST', uri);
    request.headers['Content-Type'] = 'application/json';
    request.headers['Accept'] = 'text/event-stream';
    request.body = jsonEncode({'message': message, 'session_id': sessionId});

    http.StreamedResponse response;
    try {
      response = await _client.send(request);
    } catch (e) {
      throw Exception('Connection error: $e');
    }

    if (response.statusCode != 200) {
      final body = await response.stream.bytesToString();
      throw Exception('Chat stream failed (${response.statusCode}): $body');
    }

    String pendingEventType = '';
    String pendingData = '';

    await for (final line in response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())) {
      if (line.startsWith('event: ')) {
        pendingEventType = line.substring(7).trim();
      } else if (line.startsWith('data: ')) {
        pendingData = line.substring(6).trim();
      } else if (line.isEmpty) {
        // Empty line = event boundary
        if (pendingEventType.isNotEmpty) {
          dynamic parsed;
          try {
            parsed = jsonDecode(pendingData);
          } catch (_) {
            parsed = pendingData;
          }
          yield SseEvent(type: pendingEventType, data: parsed);
          if (pendingEventType == 'done' || pendingEventType == 'error') {
            break;
          }
        }
        pendingEventType = '';
        pendingData = '';
      }
    }
  }

  /// Fetches all confirmed cart items for [sessionId].
  Future<List<CartItem>> getCartItems(String sessionId) async {
    final uri = Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/selections');
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw Exception('Failed to load cart: ${response.body}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final items = (json['items'] as List? ?? []);
    return items
        .whereType<Map<String, dynamic>>()
        .map(CartItem.fromApiJson)
        .toList();
  }

  /// Submits a post-session rating and feedback.
  Future<void> submitRating({
    required String sessionId,
    required int rating,
    required String feedback,
  }) async {
    final uri = Uri.parse('$kApiBaseUrl/api/rating');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'rating': rating,
        'feedback': feedback,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to submit rating: ${response.body}');
    }
  }

  void dispose() => _client.close();
}
