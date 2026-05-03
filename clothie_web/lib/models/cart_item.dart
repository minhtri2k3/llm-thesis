import 'package:clothie_web/config.dart';

/// A product the user has confirmed and saved to their session cart.
class CartItem {
  final String imageId;
  final String imageUrl;
  final String label;
  final String color;
  final String caption;
  final String pathMode;

  const CartItem({
    required this.imageId,
    required this.imageUrl,
    required this.label,
    this.color = '',
    this.caption = '',
    this.pathMode = 'path1',
  });

  /// Build from the backend's GET /api/sessions/{id}/selections response.
  /// The image_path field is a full disk path — extract just the filename.
  factory CartItem.fromApiJson(Map<String, dynamic> json) {
    final rawPath = json['image_path'] as String? ?? '';
    final filename = rawPath.isNotEmpty
        ? rawPath.split('/').last
        : '${json['image_id'] ?? ''}.jpg';
    return CartItem(
      imageId: json['image_id'] as String? ?? '',
      imageUrl: '$kApiBaseUrl/api/images/$filename',
      label: json['label'] as String? ?? '',
      color: json['color'] as String? ?? '',
      caption: json['caption'] as String? ?? '',
      pathMode: json['path_mode'] as String? ?? 'path1',
    );
  }

  /// Build from the agent's inline selection_confirm items payload
  /// (same shape as fromApiJson, provided for clarity).
  factory CartItem.fromAgentJson(Map<String, dynamic> json) =>
      CartItem.fromApiJson(json);
}
