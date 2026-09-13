import "package:flutter/material.dart";

import "../design/design.dart";

/// The CareerOS pathway mark: a C (career) with a rising pathway (journey/progress) exiting through
/// its opening toward a spark (achievement). Geometry mirrors
/// `.claude/skills/careeros-ui-system/assets/brand-reference/careeros-mark.svg` (64×64 viewBox).
class CareerOSMark extends StatelessWidget {
  const CareerOSMark({super.key, this.size = 40, this.onDark});

  final double size;

  /// Reversed variant (white C) for navy/dark grounds. Defaults to the current theme's brightness.
  final bool? onDark;

  @override
  Widget build(BuildContext context) {
    final reversed = onDark ?? context.colors.isDark;
    return Semantics(
      label: "CareerOS",
      image: true,
      child: SizedBox.square(
        dimension: size,
        child: CustomPaint(painter: _CareerOSMarkPainter(reversed: reversed)),
      ),
    );
  }
}

class _CareerOSMarkPainter extends CustomPainter {
  const _CareerOSMarkPainter({required this.reversed});

  final bool reversed;

  static const _pathGradientLight = [AppColors.blue, AppColors.cyan];
  static const _pathGradientDark = [AppColors.brightBlue, AppColors.cyan];

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 64, size.height / 64);

    final gradientColors = reversed ? _pathGradientDark : _pathGradientLight;
    Shader gradientFor(Rect bounds) => LinearGradient(
          begin: Alignment.bottomLeft,
          end: Alignment.topRight,
          colors: gradientColors,
        ).createShader(bounds);

    // C
    final c = Path()
      ..moveTo(49.5, 17.5)
      ..arcToPoint(const Offset(53, 41), radius: const Radius.circular(22), largeArc: true, clockwise: false);
    canvas.drawPath(
      c,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8.5
        ..strokeCap = StrokeCap.round
        ..color = reversed ? Colors.white : AppColors.navy,
    );

    // Pathway
    final pathway = Path()
      ..moveTo(17, 44)
      ..cubicTo(27, 44, 34, 38, 44.5, 27.5);
    canvas.drawPath(
      pathway,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6.5
        ..strokeCap = StrokeCap.round
        ..shader = gradientFor(pathway.getBounds()),
    );

    // Arrowhead (filled + rounded by a thin stroke of the same gradient)
    final arrow = Path()
      ..moveTo(57, 15)
      ..lineTo(51.6, 32.4)
      ..lineTo(39.6, 20.4)
      ..close();
    final arrowShader = gradientFor(arrow.getBounds());
    canvas.drawPath(arrow, Paint()..shader = arrowShader);
    canvas.drawPath(
      arrow,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..strokeJoin = StrokeJoin.round
        ..shader = arrowShader,
    );

    // Spark
    final spark = Path()
      ..moveTo(58, 4)
      ..lineTo(59.4, 7.6)
      ..lineTo(63, 9)
      ..lineTo(59.4, 10.4)
      ..lineTo(58, 14)
      ..lineTo(56.6, 10.4)
      ..lineTo(53, 9)
      ..lineTo(56.6, 7.6)
      ..close();
    canvas.drawPath(spark, Paint()..color = AppColors.cyan);

    canvas.restore();
  }

  @override
  bool shouldRepaint(_CareerOSMarkPainter oldDelegate) => oldDelegate.reversed != reversed;
}

/// "Career" in deep navy + "OS" in electric blue (reversed on dark grounds).
class CareerOSWordmark extends StatelessWidget {
  const CareerOSWordmark({super.key, this.fontSize = 24, this.onDark});

  final double fontSize;
  final bool? onDark;

  @override
  Widget build(BuildContext context) {
    final reversed = onDark ?? context.colors.isDark;
    final base = TextStyle(
      fontFamily: AppTypography.fontFamily,
      fontSize: fontSize,
      fontWeight: FontWeight.w800,
      letterSpacing: -fontSize * 0.02,
      height: 1.1,
    );
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(text: "Career", style: base.copyWith(color: reversed ? AppColors.darkTextPrimary : AppColors.navy)),
          TextSpan(text: "OS", style: base.copyWith(color: reversed ? AppColors.brightBlue : AppColors.blue)),
        ],
      ),
      semanticsLabel: "CareerOS",
      maxLines: 1,
    );
  }
}

/// Horizontal lockup: mark + wordmark.
class CareerOSLogo extends StatelessWidget {
  const CareerOSLogo({super.key, this.markSize = 36, this.onDark});

  final double markSize;
  final bool? onDark;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        CareerOSMark(size: markSize, onDark: onDark),
        SizedBox(width: markSize * 0.28),
        CareerOSWordmark(fontSize: markSize * 0.66, onDark: onDark),
      ],
    );
  }
}
