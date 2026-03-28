import 'package:flutter/material.dart';
import 'package:clothie_web/config.dart';

/// Interactive 1-10 star rating row.
///
/// Tapping a star fills all stars up to and including that index.
class StarRating extends StatefulWidget {
  final int maxStars;
  final int value; // current selected value (0 = none)
  final ValueChanged<int> onChanged;

  const StarRating({
    super.key,
    this.maxStars = kMaxStarRating,
    required this.value,
    required this.onChanged,
  });

  @override
  State<StarRating> createState() => _StarRatingState();
}

class _StarRatingState extends State<StarRating> {
  int _hovered = 0;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(widget.maxStars, (i) {
        final starIndex = i + 1;
        final isFilled = starIndex <= (
          _hovered > 0 ? _hovered : widget.value
        );
        return MouseRegion(
          onEnter: (_) => setState(() => _hovered = starIndex),
          onExit: (_) => setState(() => _hovered = 0),
          child: GestureDetector(
            onTap: () => widget.onChanged(starIndex),
            child: AnimatedScale(
              scale: _hovered == starIndex ? 1.25 : 1.0,
              duration: const Duration(milliseconds: 120),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: Icon(
                  isFilled ? Icons.star_rounded : Icons.star_outline_rounded,
                  color: isFilled
                      ? const Color(0xFFFBBF24) // amber
                      : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                  size: 28,
                ),
              ),
            ),
          ),
        );
      }),
    );
  }
}
