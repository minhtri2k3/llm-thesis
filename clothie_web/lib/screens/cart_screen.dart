import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:clothie_web/config.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/providers/cart_provider.dart';

/// Modal bottom sheet showing all confirmed items in the session cart.
class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<CartProvider>(),
        child: const CartScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      builder: (_, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Color(kSurfaceColor),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // Handle bar
              Padding(
                padding: const EdgeInsets.only(top: 12, bottom: 8),
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Header
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                child: Row(
                  children: [
                    const Icon(Icons.shopping_bag_outlined,
                        color: Color(kAccentLight), size: 22),
                    const SizedBox(width: 8),
                    Text(
                      'My Selections',
                      style: GoogleFonts.outfit(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: const Color(kTextPrimary),
                      ),
                    ),
                    const Spacer(),
                    Consumer<CartProvider>(
                      builder: (_, cart, __) => Text(
                        '${cart.count} item${cart.count == 1 ? '' : 's'}',
                        style: GoogleFonts.outfit(
                          fontSize: 13,
                          color: const Color(kTextSecondary),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              Divider(color: Colors.white.withOpacity(0.07)),

              // Content
              Expanded(
                child: Consumer<CartProvider>(
                  builder: (_, cart, __) {
                    if (cart.isLoading) {
                      return const Center(
                        child: CircularProgressIndicator(
                          color: Color(kAccentLight),
                          strokeWidth: 2,
                        ),
                      );
                    }
                    if (cart.items.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text('🛒',
                                style: TextStyle(fontSize: 48)),
                            const SizedBox(height: 12),
                            Text(
                              'No items yet',
                              style: GoogleFonts.outfit(
                                fontSize: 16,
                                color: const Color(kTextSecondary),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Pick items from the chat to add them here.',
                              style: GoogleFonts.outfit(
                                fontSize: 13,
                                color: const Color(kTextSecondary)
                                    .withOpacity(0.6),
                              ),
                            ),
                          ],
                        ),
                      );
                    }

                    return GridView.builder(
                      controller: scrollController,
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 3,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        childAspectRatio: 0.62,
                      ),
                      itemCount: cart.items.length,
                      itemBuilder: (_, i) => _CartCard(item: cart.items[i]),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _CartCard extends StatelessWidget {
  final CartItem item;
  const _CartCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(kCardColor),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.07)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Image.network(
                item.imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: const Color(kSurfaceColor),
                  child: const Icon(Icons.checkroom,
                      color: Color(kAccentLight), size: 36),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(kTextPrimary),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (item.color.isNotEmpty)
                    Text(
                      item.color,
                      maxLines: 1,
                      style: const TextStyle(
                          color: Color(kTextSecondary), fontSize: 10),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
