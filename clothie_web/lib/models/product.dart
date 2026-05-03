import 'package:clothie_web/extension/config.dart';

class Product {
  final String imageId;
  final String imageUrl;
  final String label;
  final String color;
  final String caption;
  final double score;
  final String pathMode;
  final String searchQuery;

  const Product({
    required this.imageId,
    required this.imageUrl,
    required this.label,
    this.color = '',
    this.caption = '',
    this.score = 0.0,
    this.pathMode = 'path1',
    this.searchQuery = '',
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    final imageId = json['image_id'] as String? ?? '';
    // image_path from BE is a full disk path like "/data/.../images_compressed/<uuid>.jpg"
    // Extract just the filename to build a portable URL that nginx can resolve.
    final rawPath = json['image_path'] as String? ?? '';
    final filename = rawPath.isNotEmpty
        ? rawPath.split('/').last // e.g. "ea7b6656-....jpg"
        : '$imageId.jpg'; // fallback: uuid + extension
    return Product(
      imageId: imageId,
      imageUrl: '$kApiBaseUrl/api/images/$filename',
      label: json['label'] as String? ?? '',
      color: json['color'] as String? ?? '',
      caption: json['caption'] as String? ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      pathMode: json['path_mode'] as String? ?? 'path1',
      searchQuery: json['search_query'] as String? ?? '',
    );
  }
}
