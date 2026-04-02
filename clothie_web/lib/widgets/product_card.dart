import 'package:flutter/material.dart';
import 'package:clothie_web/models/product.dart';
import 'package:clothie_web/services/api_service.dart';

/// Horizontally-scrollable row of fashion product cards.
class ProductCardList extends StatelessWidget {
  final List<Product> products;
  final String sessionId;
  const ProductCardList({super.key, required this.products, required this.sessionId});

  @override
  Widget build(BuildContext context) {
    if (products.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: SizedBox(
        height: 220,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: products.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) => _ProductCard(
            product: products[i],
            productIndex: i,
            sessionId: sessionId,
          ),
        ),
      ),
    );
  }
}

class _ProductCard extends StatefulWidget {
  final Product product;
  final int productIndex;
  final String sessionId;
  const _ProductCard({
    required this.product,
    required this.productIndex,
    required this.sessionId,
  });

  @override
  State<_ProductCard> createState() => _ProductCardState();
}

class _ProductCardState extends State<_ProductCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: () {
          // Log click — fire-and-forget
          ApiService().logClick(
            widget.sessionId,
            widget.product.imageId,
            widget.productIndex + 1, // 1-based position
          );
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          width: 130,
          decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _hovered
                ? theme.colorScheme.primary
                : (isDark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.08)),
            width: 1,
          ),
          boxShadow: _hovered
              ? [
                  BoxShadow(
                    color: theme.colorScheme.primary.withValues(alpha: 0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ]
              : [],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Image section
              Expanded(
                child: Image.network(
                  widget.product.imageUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    color: theme.scaffoldBackgroundColor,
                    child: Icon(Icons.checkroom,
                        color: theme.colorScheme.primary, size: 36),
                  ),
                  loadingBuilder: (_, child, progress) {
                    if (progress == null) return child;
                    return Container(
                      color: theme.scaffoldBackgroundColor,
                      child: Center(
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    );
                  },
                ),
              ),
              // Label section
              Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.product.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: theme.colorScheme.onSurface,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (widget.product.color.isNotEmpty)
                      Text(
                        widget.product.color,
                        maxLines: 1,
                        style: TextStyle(
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.7), fontSize: 10),
                      ),
                  ],
                ),
              ),
            ],
          ),
          ),
        ),
      ),
    );
  }
}
