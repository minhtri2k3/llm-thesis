import 'package:flutter/material.dart';
import 'package:clothie_web/models/chat_message.dart';

/// Animated thinking indicator shown while the AI is reasoning.
///
/// Shows a pulsing 3-dot animation during `thinking` state,
/// progressive thinking steps as they arrive, then collapses
/// to a summary line when thinking ends.
class ThinkingIndicator extends StatefulWidget {
  final List<ThinkingStep> steps;
  final bool isDone; // true once thinking_end has fired

  const ThinkingIndicator({
    super.key,
    required this.steps,
    required this.isDone,
  });

  @override
  State<ThinkingIndicator> createState() => _ThinkingIndicatorState();
}

class _ThinkingIndicatorState extends State<ThinkingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _dotController;
  bool _expanded = false;

  @override
  void initState() {
    super.initState();
    _dotController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _dotController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isDone && widget.steps.isEmpty) {
      return _buildPulseDots();
    }
    if (widget.isDone) {
      return _buildCollapsed();
    }
    return _buildSteps();
  }

  Widget _buildPulseDots() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) {
        return AnimatedBuilder(
          animation: _dotController,
          builder: (context, __) {
            final t = (_dotController.value - i * 0.15).clamp(0.0, 1.0);
            final opacity = (0.3 + 0.7 * (0.5 - (t - 0.5).abs() * 2).clamp(0.0, 0.5));
            return Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Opacity(
                opacity: opacity.clamp(0.3, 1.0),
                child: Text('●',
                    style: TextStyle(
                        color: Theme.of(context).colorScheme.primary, fontSize: 10)),
              ),
            );
          },
        );
      }),
    );
  }

  Widget _buildCollapsed() {
    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.check_circle,
                  size: 14, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 4),
              Text(
                'Thought for a moment  ${_expanded ? '▲' : '▼'}',
                style: TextStyle(
                  fontSize: 11,
                  color: Theme.of(context).colorScheme.primary,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
          if (_expanded) ...[
            const SizedBox(height: 6),
            ..._buildStepsList(),
          ]
        ],
      ),
    );
  }

  Widget _buildSteps() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          _buildPulseDots(),
          const SizedBox(width: 8),
          Text('Thinking...',
              style: TextStyle(
                  fontSize: 11,
                  color: Theme.of(context).colorScheme.primary,
                  fontStyle: FontStyle.italic)),
        ]),
        if (widget.steps.isNotEmpty) ...[
          const SizedBox(height: 6),
          ..._buildStepsList(),
        ]
      ],
    );
  }

  List<Widget> _buildStepsList() {
    return widget.steps.map((s) => Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.subdirectory_arrow_right,
              size: 12, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6)),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              s.text,
              style: TextStyle(
                  fontSize: 11, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6)),
            ),
          ),
        ],
      ),
    )).toList();
  }
}
