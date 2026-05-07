import 'package:flutter_test/flutter_test.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/models/product.dart';
import 'package:clothie_web/screens/chat/chat_provider.dart';
import 'package:clothie_web/services/api_service.dart';

class _FakeApiService extends ApiService {
  bool shouldThrow = false;
  Map<String, dynamic>? lastPayload;

  @override
  Future<Map<String, dynamic>> addDirectSelection({
    required String sessionId,
    required String imageId,
    required String label,
    required String imagePath,
    required int position,
    String color = '',
    String caption = '',
    String searchQuery = '',
    String pathMode = 'path2',
  }) async {
    if (shouldThrow) {
      throw Exception('direct add failed');
    }
    lastPayload = {
      'sessionId': sessionId,
      'imageId': imageId,
      'label': label,
      'imagePath': imagePath,
      'position': position,
      'color': color,
      'caption': caption,
      'searchQuery': searchQuery,
      'pathMode': pathMode,
    };
    return {'ok': true, 'inserted': 1, 'already_exists': 0};
  }
}

void main() {
  test('PATH2 direct add updates cart notification state', () async {
    final api = _FakeApiService();
    var onSelectionSavedCalled = false;
    final provider = ChatProvider(
      api: api,
      onSelectionSaved: () => onSelectionSavedCalled = true,
    );
    provider.setSessionId('s-path2');

    const product = Product(
      imageId: 'img-1',
      imageUrl: 'http://localhost:8000/api/images/img-1.jpg',
      label: 'Dress',
      color: 'Blue',
      caption: 'sample',
      pathMode: 'path2',
      searchQuery: '__path2_image__',
    );

    final ok = await provider.addPath2ProductToCart(product, 2);

    expect(ok, isTrue);
    expect(onSelectionSavedCalled, isTrue);
    expect(provider.pendingCartNotification, isTrue);
    expect(api.lastPayload, isNotNull);
    expect(api.lastPayload!['pathMode'], 'path2');
    expect(api.lastPayload!['imagePath'], 'img-1.jpg');
  });

  test('PATH2 direct add surfaces error state when API fails', () async {
    final api = _FakeApiService()..shouldThrow = true;
    final provider = ChatProvider(api: api);
    provider.setSessionId('s-path2');

    const product = Product(
      imageId: 'img-2',
      imageUrl: 'http://localhost:8000/api/images/img-2.jpg',
      label: 'Top',
      pathMode: 'path2',
    );

    final ok = await provider.addPath2ProductToCart(product, 1);

    expect(ok, isFalse);
    expect(provider.pendingCartNotification, isFalse);
    expect(provider.error, isNotNull);
  });

  test('CartItem preserves PATH2 attribution from API payload', () {
    final item = CartItem.fromApiJson({
      'image_id': 'img-3',
      'image_path': 'img-3.jpg',
      'label': 'Skirt',
      'path_mode': 'path2',
    });

    expect(item.pathMode, 'path2');
  });
}
