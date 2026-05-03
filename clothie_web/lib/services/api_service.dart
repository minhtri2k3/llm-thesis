import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:clothie_web/extension/config.dart';
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
  ///
  /// [userName] is the display name entered at registration.
  /// [yearOfBirth] and [gender] are demographic fields for thesis research.
  Future<String> createSession(
    String userName,
    int yearOfBirth,
    String gender,
    String preferredModel,
  ) async {
    final uri = Uri.parse('$kApiBaseUrl/api/sessions');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_name': userName,
        'year_of_birth': yearOfBirth,
        'gender': gender,
        'preferred_model': preferredModel,
      }),
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

    await for (final line
        in response.stream
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

  /// Fetches all session ratings for the leaderboard view.
  Future<List<Map<String, dynamic>>> getRatings() async {
    final uri = Uri.parse('$kApiBaseUrl/api/ratings');
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw Exception('Failed to load ratings: ${response.body}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return (json['entries'] as List? ?? [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  /// Fetches per-session LLM token analytics for the professor dashboard.
  ///
  /// Requires the correct [secretKey] matching the backend ADMIN_SECRET_KEY.
  /// Throws an [Exception] whose message contains the HTTP status if auth fails.
  Future<List<Map<String, dynamic>>> getTokenAnalytics(String secretKey) async {
    final uri = Uri.parse('$kApiBaseUrl/api/analytics/token-usage');
    final response = await _client.get(
      uri,
      headers: {'X-Admin-Key': secretKey},
    );
    if (response.statusCode == 403) {
      throw Exception('403: Incorrect access code');
    }
    if (response.statusCode == 503) {
      throw Exception('503: Analytics not configured on server');
    }
    if (response.statusCode != 200) {
      throw Exception('Failed to load analytics: ${response.body}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return (json['sessions'] as List? ?? [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  /// Fetches demographic aggregate stats for the professor dashboard.
  ///
  /// Returns a map with keys `by_gender` and `by_age_group`.
  /// Throws an [Exception] on auth failure or server error.
  Future<Map<String, dynamic>> getDemographics(String secretKey) async {
    final uri = Uri.parse('$kApiBaseUrl/api/demographics');
    final response = await _client.get(
      uri,
      headers: {'X-Admin-Key': secretKey},
    );
    if (response.statusCode == 403) {
      throw Exception('403: Incorrect access code');
    }
    if (response.statusCode == 503) {
      throw Exception('503: Demographics not configured on server');
    }
    if (response.statusCode != 200) {
      throw Exception('Failed to load demographics: ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// Fetches behavior funnel analytics with path comparison and integrity data.
  ///
  /// Returns a map containing `path_comparison`, `aggregate`, and `integrity`.
  /// Throws an [Exception] on auth failure or server error.
  Future<Map<String, dynamic>> getBehaviourFunnel(String secretKey) async {
    final uri = Uri.parse('$kApiBaseUrl/api/analytics/behaviour-funnel');
    final response = await _client.get(
      uri,
      headers: {'X-Admin-Key': secretKey},
    );
    if (response.statusCode == 403) {
      throw Exception('403: Incorrect access code');
    }
    if (response.statusCode == 503) {
      throw Exception('503: Analytics not configured on server');
    }
    if (response.statusCode != 200) {
      throw Exception('Failed to load behavior funnel: ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// Submits a post-session rating and feedback.
  Future<void> submitRating({
    required String sessionId,
    required int ratingOverall,
    required int ratingSuggestions,
    required int ratingConversation,
    String feedback = '',
  }) async {
    final uri = Uri.parse('$kApiBaseUrl/api/rating');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'rating_overall': ratingOverall,
        'rating_suggestions': ratingSuggestions,
        'rating_conversation': ratingConversation,
        'feedback': feedback,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to submit rating: ${response.body}');
    }
  }

  // ── Behaviour Analytics ──────────────────────────────────────────────────

  /// Batch-log product impressions shown in a search result.
  /// Fire-and-forget — analytics errors must never disrupt the chat.
  Future<void> logImpressions(
    String sessionId,
    List<Map<String, dynamic>> items,
  ) async {
    try {
      final resp = await _client.post(
        Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/impressions'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'items': items}),
      );
      if (resp.statusCode != 200 && kDebugMode) {
        debugPrint(
          'telemetry(logImpressions) failed: ${resp.statusCode} ${resp.body}',
        );
      }
    } catch (_) {
      if (kDebugMode) {
        debugPrint('telemetry(logImpressions) network failure');
      }
    }
  }

  /// Log a product card tap event (fire-and-forget).
  Future<void> logClick(
    String sessionId,
    String imageId,
    int position, {
    String searchQuery = '',
    String pathMode = 'path1',
  }) async {
    try {
      final resp = await _client.post(
        Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/clicks'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_id': imageId,
          'position': position,
          'search_query': searchQuery,
          'path_mode': pathMode,
        }),
      );
      if (resp.statusCode != 200 && kDebugMode) {
        debugPrint(
          'telemetry(logClick) failed: ${resp.statusCode} ${resp.body}',
        );
      }
    } catch (_) {
      if (kDebugMode) {
        debugPrint('telemetry(logClick) network failure');
      }
    }
  }

  /// Log a purchase intent signal ('will_buy' | 'not_for_me').
  /// Throws on failure — this is an explicit user action.
  Future<void> logIntent(
    String sessionId,
    String imageId,
    String intentType, {
    String reason = '',
    String pathMode = 'path1',
  }) async {
    final resp = await _client.post(
      Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/intents'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'image_id': imageId,
        'intent_type': intentType,
        'reason': reason,
        'path_mode': pathMode,
      }),
    );
    if (resp.statusCode != 200) {
      throw Exception('logIntent failed: ${resp.body}');
    }
  }

  /// Place a simulated order (phone + address). Returns the new order ID.
  /// Also marks the session as ended in the backend.
  Future<int> placeOrder(
    String sessionId,
    String phone,
    String address, {
    String? pathMode,
  }) async {
    final body = <String, dynamic>{'phone': phone, 'address': address};
    if (pathMode != null && pathMode.isNotEmpty) {
      body['path_mode'] = pathMode;
    }
    final resp = await _client.post(
      Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/orders'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    if (resp.statusCode != 200) {
      throw Exception('Order failed: ${resp.body}');
    }
    return (jsonDecode(resp.body) as Map<String, dynamic>)['order_id'] as int;
  }

  Future<void> removeCartItem(String sessionId, String imageId) async {
    final resp = await _client.delete(
      Uri.parse('$kApiBaseUrl/api/sessions/$sessionId/selections/$imageId'),
    );
    if (resp.statusCode != 200) {
      throw Exception('Failed to remove item: ${resp.body}');
    }
  }

  /// PATH 2: search visually similar items by query image.
  ///
  /// Uses a dedicated backend endpoint isolated from PATH 1 chat flow.
  Future<List<Map<String, dynamic>>> searchByImage({
    required String sessionId,
    required Uint8List imageBytes,
    required String filename,
    int topK = 6,
  }) async {
    final req = http.MultipartRequest(
      'POST',
      Uri.parse('$kApiBaseUrl/api/path2/image-search'),
    );
    req.fields['session_id'] = sessionId;
    req.fields['top_k'] = topK.toString();
    req.files.add(
      http.MultipartFile.fromBytes('image', imageBytes, filename: filename),
    );

    final streamed = await _client.send(req);
    final resp = await http.Response.fromStream(streamed);
    if (resp.statusCode != 200) {
      throw Exception(
        'PATH 2 image search failed (${resp.statusCode}): ${resp.body}',
      );
    }
    final json = jsonDecode(resp.body) as Map<String, dynamic>;
    return (json['products'] as List? ?? [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  void dispose() => _client.close();
}
