import 'package:flutter/material.dart';
import 'package:clothie_web/models/product.dart';
import 'package:clothie_web/services/api_service.dart';

/// Horizontally-scrollable row of fashion product cards.
class ProductCardList extends StatelessWidget {
  final List<Product> products;
  final String sessionId;
  final Function(int)? onCartTap;
  const ProductCardList({
    super.key,
    required this.products,
    required this.sessionId,
    this.onCartTap,
  });

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
            onCartTap: onCartTap,
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
  final Function(int)? onCartTap;
  const _ProductCard({
    required this.product,
    required this.productIndex,
    required this.sessionId,
    this.onCartTap,
  });

  @override
  State<_ProductCard> createState() => _ProductCardState();
}

class _ProductCardState extends State<_ProductCard> {
  bool _hovered = false;

  void _showFullscreenImage(
    BuildContext context,
    String imageUrl,
    String label, {
    VoidCallback? onAddToCart,
  }) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.9),
      builder: (ctx) => Stack(
        fit: StackFit.expand,
        children: [
          InteractiveViewer(
            panEnabled: true,
            boundaryMargin: const EdgeInsets.all(20),
            minScale: 0.5,
            maxScale: 4.0,
            child: GestureDetector(
              onTap: () => Navigator.of(ctx).pop(),
              child: Image.network(
                imageUrl,
                fit: BoxFit.contain,
              ),
            ),
          ),
          Positioned(
            top: 40,
            right: 20,
            child: Material(
              color: Colors.transparent,
              child: IconButton(
                icon: const Icon(Icons.close, color: Colors.white, size: 30),
                onPressed: () => Navigator.of(ctx).pop(),
              ),
            ),
          ),
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Material(
              color: Colors.transparent,
              child: Text(
                label,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  decoration: TextDecoration.none,
                ),
              ),
            ),
          ),
          if (onAddToCart != null)
            Positioned(
              left: 20,
              bottom: 100,
              child: Material(
                color: Colors.transparent,
                child: FloatingActionButton.extended(
                  backgroundColor: Theme.of(ctx).colorScheme.primary,
                  foregroundColor: Theme.of(ctx).colorScheme.onPrimary,
                  icon: const Icon(Icons.shopping_cart_rounded),
                  label: const Text('Add to Cart'),
                  onPressed: onAddToCart,
                ),
              ),
            ),
        ],
      ),
    );
  }

  void _showAddToCartDialog(
    BuildContext context,
    Product product,
    VoidCallback onConfirm,
  ) {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('\u{1F6D2} Add to cart?'),
        content: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(
                product.imageUrl,
                width: 72,
                height: 72,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  width: 72,
                  height: 72,
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.checkroom),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.label,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  if (product.color.isNotEmpty)
                    Text(
                      product.color,
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(context)
                            .colorScheme
                            .onSurface
                            .withValues(alpha: 0.6),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              onConfirm();
            },
            child: const Text('Add to Cart \u2713'),
          ),
        ],
      ),
    );
  }

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
          _showFullscreenImage(
            context,
            widget.product.imageUrl,
            widget.product.label,
            onAddToCart: widget.onCartTap != null
                ? () {
                    Navigator.pop(context); // close fullscreen first
                    _showAddToCartDialog(
                      context,
                      widget.product,
                      () => widget.onCartTap!(widget.productIndex + 1),
                    );
                  }
                : null,
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
