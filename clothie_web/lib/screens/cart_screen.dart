import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:clothie_web/models/cart_item.dart';
import 'package:clothie_web/providers/cart_provider.dart';
import 'package:clothie_web/services/api_service.dart';

/// Modal bottom sheet showing all confirmed items in the session cart.
class CartScreen extends StatelessWidget {
  final String sessionId;
  const CartScreen({super.key, required this.sessionId});

  static Future<void> show(BuildContext context, String sessionId) {
    // Refresh cart from backend before opening
    context.read<CartProvider>().reload();
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<CartProvider>(),
        child: CartScreen(sessionId: sessionId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      builder: (_, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
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
                    Icon(Icons.shopping_bag_outlined,
                        color: theme.colorScheme.primary, size: 22),
                    const SizedBox(width: 8),
                    Text(
                      'My Selections',
                      style: GoogleFonts.outfit(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                    const Spacer(),
                    Consumer<CartProvider>(
                      builder: (_, cart, __) => Text(
                        '${cart.count} item${cart.count == 1 ? '' : 's'}',
                        style: GoogleFonts.outfit(
                          fontSize: 13,
                          color: theme.colorScheme.onSurface.withOpacity(0.7),
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
                      return Center(
                        child: CircularProgressIndicator(
                          color: theme.colorScheme.primary,
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
                                color: theme.colorScheme.onSurface.withOpacity(0.7),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Pick items from the chat to add them here.',
                              style: GoogleFonts.outfit(
                                fontSize: 13,
                                color: theme.colorScheme.onSurface.withOpacity(0.5),
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
                      itemBuilder: (_, i) => _CartCard(item: cart.items[i], sessionId: cart.sessionId),
                    );
                  },
                ),
              ),

              // ── Let's make the order CTA ────────────────────────────────
              Consumer<CartProvider>(
                builder: (_, cart, __) {
                  if (cart.count == 0) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    child: SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: const Text('📦'),
                        label: Text(
                          "Let's make the order",
                          style: GoogleFonts.outfit(fontWeight: FontWeight.w600),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: theme.colorScheme.primary,
                          foregroundColor: theme.colorScheme.onPrimary,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        onPressed: () => _showOrderDialog(context, sessionId),
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _showOrderDialog(BuildContext context, String sessionId) {
    final phoneCtrl = TextEditingController();
    final addressCtrl = TextEditingController();

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          '📦 Place Your Order',
          style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(
                labelText: '📱 Phone number',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: addressCtrl,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: '🏠 Delivery address',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final phone = phoneCtrl.text.trim();
              final address = addressCtrl.text.trim();
              if (phone.isEmpty || address.isEmpty) return;
              try {
                await ApiService().placeOrder(sessionId, phone, address);
                if (ctx.mounted) Navigator.pop(ctx);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("🎉 Order placed! We'll be in touch."),
                    ),
                  );
                }
              } catch (e) {
                if (ctx.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Error: $e')),
                  );
                }
              }
            },
            child: Text('Confirm Order ✓', style: GoogleFonts.outfit()),
          ),
        ],
      ),
    );
  }
}

class _CartCard extends StatefulWidget {
  final CartItem item;
  final String sessionId;
  const _CartCard({required this.item, required this.sessionId});

  @override
  State<_CartCard> createState() => _CartCardState();
}

class _CartCardState extends State<_CartCard> {
  String? _intentLogged;   // null | 'will_buy' | 'not_for_me'
  bool _sending = false;

  Future<void> _logIntent(String type) async {
    if (_sending || _intentLogged != null) return;
    setState(() => _sending = true);
    try {
      await ApiService().logIntent(widget.sessionId, widget.item.imageId, type);
      setState(() => _intentLogged = type);
    } catch (_) {
      // Best-effort — silently fail
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: theme.brightness == Brightness.dark 
              ? Colors.white.withOpacity(0.07) 
              : Colors.black.withOpacity(0.05),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Image.network(
                widget.item.imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: theme.colorScheme.surface,
                  child: Icon(Icons.checkroom,
                      color: theme.colorScheme.primary, size: 36),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.item.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: theme.colorScheme.onSurface,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (widget.item.color.isNotEmpty)
                    Text(
                      widget.item.color,
                      maxLines: 1,
                      style: TextStyle(
                          color: theme.colorScheme.onSurface.withOpacity(0.7), fontSize: 10),
                    ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      IconButton(
                        iconSize: 20,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        icon: Icon(
                          _intentLogged == 'will_buy'
                              ? Icons.thumb_up
                              : Icons.thumb_up_outlined,
                          color: _intentLogged == 'will_buy'
                              ? Colors.green
                              : theme.colorScheme.onSurface.withOpacity(0.5),
                          size: 18,
                        ),
                        tooltip: "I'll buy this",
                        onPressed: _sending ? null : () => _logIntent('will_buy'),
                      ),
                      const SizedBox(width: 4),
                      IconButton(
                        iconSize: 20,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        icon: Icon(
                          _intentLogged == 'not_for_me'
                              ? Icons.thumb_down
                              : Icons.thumb_down_outlined,
                          color: _intentLogged == 'not_for_me'
                              ? Colors.red
                              : theme.colorScheme.onSurface.withOpacity(0.5),
                          size: 18,
                        ),
                        tooltip: "Not for me",
                        onPressed: _sending ? null : () => _logIntent('not_for_me'),
                      ),
                    ],
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
