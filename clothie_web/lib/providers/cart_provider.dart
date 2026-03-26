import 'package:flutter/foundation.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/services/api_service.dart';

/// Manages the user's in-session cart (confirmed product selections).
///
/// Updated in two ways:
///   1. Eagerly: when [addItems] is called from [ChatProvider] after a
///      `selection_saved` SSE event (instant badge update, no extra request).
///   2. Lazily: [reload] fetches from GET /api/sessions/{id}/selections;
///      called on [CartScreen] open to ensure the list is authoritative.
class CartProvider extends ChangeNotifier {
  final ApiService _api;
  final String sessionId;

  final List<CartItem> _items = [];
  bool _isLoading = false;
  String? _error;

  CartProvider({required this.sessionId, ApiService? api})
      : _api = api ?? ApiService();

  List<CartItem> get items => List.unmodifiable(_items);
  int get count => _items.length;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Called by ChatProvider when `selection_saved` SSE fires.
  /// Reloads the cart from the authoritative API endpoint.
  void onSelectionSaved() => reload();

  /// Fetches authoritative cart from the backend.
  Future<void> reload() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final fetched = await _api.getCartItems(sessionId);
      _items
        ..clear()
        ..addAll(fetched);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
