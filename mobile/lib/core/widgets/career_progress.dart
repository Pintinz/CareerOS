import "dart:math" as math;

import "package:flutter/material.dart";

import "../design/design.dart";

/// The light end of a progress gradient: the same hue, a step brighter.
Color _lighten(Color color) => Color.lerp(color, Colors.white, 0.35)!;

/// Rounded linear progress with an accessible label. [value] is 0–1.
class CareerProgressBar extends StatelessWidget {
  const CareerProgressBar({
    super.key,
    required this.value,
    required this.semanticLabel,
    this.semanticValue,
    this.tone = AppTone.primary,
    this.height = 8,
    this.trackColor,
  });

  final double value;
  final String semanticLabel;
  final String? semanticValue;
  final AppTone tone;
  final double height;
  final Color? trackColor;

  @override
  Widget build(BuildContext context) {
    final clamped = value.clamp(0.0, 1.0);
    final color = tone.color(context);
    return Semantics(
      label: semanticLabel,
      value: semanticValue ?? "${(clamped * 100).round()}%",
      child: ClipRRect(
        borderRadius: AppRadius.pillAll,
        child: Container(
          height: height,
          color: trackColor ?? tone.tint(context),
          alignment: Alignment.centerLeft,
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: clamped),
            duration: AppMotion.of(context),
            curve: AppMotion.curve,
            builder: (context, animated, _) => FractionallySizedBox(
              widthFactor: animated,
              heightFactor: 1,
              // A soft same-hue gradient reads as a crafted brand bar rather than a stock indicator.
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: AppRadius.pillAll,
                  gradient: LinearGradient(colors: [_lighten(color), color]),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Circular score/progress ring with centered content (score heroes, setup progress).
class CareerProgressRing extends StatelessWidget {
  const CareerProgressRing({
    super.key,
    required this.value,
    required this.semanticLabel,
    this.semanticValue,
    this.size = 96,
    this.strokeWidth = 9,
    this.tone = AppTone.primary,
    this.trackColor,
    this.color,
    this.child,
  });

  final double value;
  final String semanticLabel;
  final String? semanticValue;
  final double size;
  final double strokeWidth;
  final AppTone tone;
  final Color? trackColor;

  /// Overrides the tone color (e.g. white on a hero gradient).
  final Color? color;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final clamped = value.clamp(0.0, 1.0);
    final ringColor = color ?? tone.color(context);
    return Semantics(
      label: semanticLabel,
      value: semanticValue ?? "${(clamped * 100).round()}%",
      child: SizedBox.square(
        dimension: size,
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: clamped),
          duration: AppMotion.of(context, AppMotion.slow),
          curve: AppMotion.curve,
          builder: (context, animated, inner) => CustomPaint(
            painter: _RingPainter(
              value: animated,
              strokeWidth: strokeWidth,
              color: ringColor,
              trackColor: trackColor ?? ringColor.withValues(alpha: 0.15),
            ),
            child: inner,
          ),
          child: Center(child: ExcludeSemantics(child: child ?? const SizedBox.shrink())),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter({required this.value, required this.strokeWidth, required this.color, required this.trackColor});

  final double value;
  final double strokeWidth;
  final Color color;
  final Color trackColor;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset(strokeWidth / 2, strokeWidth / 2) & Size(size.width - strokeWidth, size.height - strokeWidth);
    final track = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..color = trackColor;
    canvas.drawArc(rect, 0, math.pi * 2, false, track);
    if (value <= 0) return;
    final sweep = math.pi * 2 * value;
    final progress = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: 0,
        endAngle: math.max(sweep, 0.01),
        colors: [_lighten(color), color],
        transform: const GradientRotation(-math.pi / 2),
      ).createShader(rect);
    canvas.drawArc(rect, -math.pi / 2, sweep, false, progress);
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.value != value || old.color != color || old.trackColor != trackColor || old.strokeWidth != strokeWidth;
}
