import "dart:math" as math;

import "package:flutter/material.dart";

import "../../../core/design/design.dart";

/// Flat, blue-monochrome onboarding illustrations in the style of the CareerOS mockup board.
///
/// Every scene is drawn on a 320 × 260 design canvas and scaled to fit, so it stays crisp at any
/// size, follows light/dark mode, and never shows numbers or data (illustrations, not results).
enum OnboardingScene { climb, opportunities, prepare, track }

class OnboardingIllustration extends StatelessWidget {
  const OnboardingIllustration({super.key, required this.scene});

  final OnboardingScene scene;

  static const _canvas = Size(320, 260);

  @override
  Widget build(BuildContext context) {
    final palette = _Palette.of(context);
    return ExcludeSemantics(
      child: FittedBox(
        child: SizedBox.fromSize(
          size: _canvas,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned.fill(child: CustomPaint(painter: _BackdropPainter(palette))),
              ...switch (scene) {
                OnboardingScene.climb => [Positioned.fill(child: CustomPaint(painter: _ClimbPainter(palette)))],
                OnboardingScene.opportunities => _opportunities(context, palette),
                OnboardingScene.prepare => _prepare(context, palette),
                OnboardingScene.track => _track(context, palette),
              },
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------------------------------------
  // Opportunities: a search bar over a stack of opportunity cards.
  // ------------------------------------------------------------------------------------------------

  List<Widget> _opportunities(BuildContext context, _Palette p) => [
        Positioned(
          left: 58,
          top: 20,
          width: 204,
          height: 40,
          child: _Panel(
            palette: p,
            radius: AppRadius.pill,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(
              children: [
                Icon(AppIcons.search, size: 20, color: p.primary),
                const SizedBox(width: 10),
                _Bar(width: 96, color: p.line),
                const Spacer(),
                Icon(AppIcons.filter, size: 18, color: p.muted),
              ],
            ),
          ),
        ),
        Positioned(
          left: 34,
          top: 82,
          width: 196,
          height: 74,
          child: Transform.rotate(
            angle: -0.07,
            child: _Panel(palette: p, elevated: false, child: _OpportunityRow(palette: p, icon: AppIcons.scholarship, tone: p.soft)),
          ),
        ),
        Positioned(
          left: 86,
          top: 116,
          width: 214,
          height: 86,
          child: _Panel(palette: p, child: _OpportunityRow(palette: p, icon: AppIcons.job, tone: p.primary, saved: true)),
        ),
        Positioned(
          left: 50,
          top: 208,
          width: 176,
          height: 44,
          child: _Panel(
            palette: p,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                Icon(AppIcons.location, size: 18, color: p.primary),
                const SizedBox(width: 8),
                _Bar(width: 70, color: p.line),
                const Spacer(),
                _Pill(width: 40, color: p.tint),
              ],
            ),
          ),
        ),
        Positioned(left: 262, top: 70, child: _Badge(palette: p, icon: AppIcons.savedSelected, size: 38)),
        Positioned(left: 26, top: 36, child: _Spark(size: 22, color: p.accent)),
        Positioned(left: 286, top: 214, child: _Spark(size: 14, color: p.primary)),
      ];

  // ------------------------------------------------------------------------------------------------
  // Prepare: a practice checklist, an interview bubble and a progress ring.
  // ------------------------------------------------------------------------------------------------

  List<Widget> _prepare(BuildContext context, _Palette p) => [
        Positioned(
          left: 36,
          top: 30,
          width: 176,
          height: 204,
          child: _Panel(
            palette: p,
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(color: p.tint, borderRadius: AppRadius.smAll),
                      child: Icon(AppIcons.aptitude, size: 18, color: p.primary),
                    ),
                    const SizedBox(width: 10),
                    _Bar(width: 84, color: p.deep, height: 9),
                  ],
                ),
                const SizedBox(height: 14),
                for (final (done, width) in [(true, 96.0), (true, 72.0), (true, 88.0), (false, 64.0)]) ...[
                  Row(
                    children: [
                      _CheckDot(palette: p, done: done),
                      const SizedBox(width: 10),
                      _Bar(width: width, color: done ? p.line : p.line.withValues(alpha: 0.6)),
                    ],
                  ),
                  const SizedBox(height: 10),
                ],
              ],
            ),
          ),
        ),
        Positioned(
          left: 196,
          top: 22,
          width: 100,
          height: 64,
          child: CustomPaint(
            painter: _BubblePainter(p.primary),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 20),
              child: Row(
                children: [
                  Icon(AppIcons.microphone, size: 22, color: p.onPrimary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _Bar(width: 48, color: p.onPrimary.withValues(alpha: 0.9), height: 6),
                        const SizedBox(height: 6),
                        _Bar(width: 32, color: p.onPrimary.withValues(alpha: 0.6), height: 6),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        Positioned(
          left: 190,
          top: 118,
          width: 104,
          height: 104,
          child: _Panel(
            palette: p,
            radius: 52,
            padding: const EdgeInsets.all(14),
            child: CustomPaint(
              painter: _RingPainter(track: p.tint, value: p.primary, fraction: 0.72),
              child: Center(child: Icon(AppIcons.analytics, size: 30, color: p.primary)),
            ),
          ),
        ),
        Positioned(left: 20, top: 214, child: _Spark(size: 18, color: p.accent)),
        Positioned(left: 292, top: 100, child: _Spark(size: 12, color: p.primary)),
      ];

  // ------------------------------------------------------------------------------------------------
  // Track: an application timeline from applied to offer.
  // ------------------------------------------------------------------------------------------------

  List<Widget> _track(BuildContext context, _Palette p) => [
        Positioned(
          left: 34,
          top: 24,
          width: 184,
          height: 212,
          child: _Panel(
            palette: p,
            padding: const EdgeInsets.fromLTRB(14, 16, 14, 12),
            child: Column(
              children: [
                for (final (i, state) in _TimelineState.values.indexed)
                  Expanded(child: _TimelineRow(palette: p, state: state, last: i == _TimelineState.values.length - 1)),
              ],
            ),
          ),
        ),
        Positioned(left: 222, top: 44, child: _Badge(palette: p, icon: AppIcons.achievement, size: 70, tone: p.warm)),
        Positioned(
          left: 214,
          top: 142,
          width: 86,
          height: 80,
          child: _Panel(
            palette: p,
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                Container(
                  height: 22,
                  decoration: BoxDecoration(
                    color: p.primary,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(AppRadius.md)),
                  ),
                ),
                Expanded(child: Center(child: Icon(AppIcons.deadline, size: 28, color: p.primary))),
              ],
            ),
          ),
        ),
        Positioned(left: 292, top: 26, child: _Spark(size: 18, color: p.accent)),
        Positioned(left: 16, top: 226, child: _Spark(size: 12, color: p.primary)),
      ];
}

// --------------------------------------------------------------------------------------------------
// Palette
// --------------------------------------------------------------------------------------------------

class _Palette {
  const _Palette({
    required this.blob,
    required this.blobSoft,
    required this.primary,
    required this.deep,
    required this.soft,
    required this.tint,
    required this.line,
    required this.muted,
    required this.card,
    required this.cardBorder,
    required this.accent,
    required this.warm,
    required this.success,
    required this.onPrimary,
    required this.isDark,
  });

  factory _Palette.of(BuildContext context) {
    final c = context.colors;
    final primary = c.primary;
    return _Palette(
      blob: primary.withValues(alpha: c.isDark ? 0.14 : 0.09),
      blobSoft: primary.withValues(alpha: c.isDark ? 0.07 : 0.05),
      primary: primary,
      deep: c.isDark ? Color.lerp(AppColors.brightBlue, Colors.white, 0.35)! : Color.lerp(AppColors.navy, AppColors.blue, 0.45)!,
      soft: Color.alphaBlend(primary.withValues(alpha: c.isDark ? 0.45 : 0.35), c.surface),
      tint: c.tint(primary),
      line: c.isDark ? c.border : Color.alphaBlend(primary.withValues(alpha: 0.12), c.surfaceMuted),
      muted: c.textSecondary,
      card: c.surfaceElevated,
      cardBorder: c.border,
      accent: AppColors.cyan,
      warm: AppColors.warning,
      success: AppColors.success,
      onPrimary: Colors.white,
      isDark: c.isDark,
    );
  }

  final Color blob;
  final Color blobSoft;
  final Color primary;
  final Color deep;
  final Color soft;
  final Color tint;
  final Color line;
  final Color muted;
  final Color card;
  final Color cardBorder;
  final Color accent;
  final Color warm;
  final Color success;
  final Color onPrimary;
  final bool isDark;
}

// --------------------------------------------------------------------------------------------------
// Shared pieces
// --------------------------------------------------------------------------------------------------

class _BackdropPainter extends CustomPainter {
  const _BackdropPainter(this.p);

  final _Palette p;

  @override
  void paint(Canvas canvas, Size size) {
    // Soft organic blob behind the scene, plus a few floating tiles.
    final blob = Path()
      ..moveTo(40, 150)
      ..cubicTo(20, 80, 90, 18, 170, 22)
      ..cubicTo(250, 26, 312, 76, 302, 146)
      ..cubicTo(294, 212, 232, 250, 158, 246)
      ..cubicTo(88, 242, 56, 214, 40, 150)
      ..close();
    canvas.drawPath(blob, Paint()..color = p.blob);
    canvas.drawCircle(const Offset(68, 60), 30, Paint()..color = p.blobSoft);

    final tile = Paint()..color = p.blob;
    for (final (offset, side, angle) in [(const Offset(284, 188), 16.0, 0.5), (const Offset(20, 118), 12.0, 0.3), (const Offset(244, 12), 10.0, 0.8)]) {
      canvas.save();
      canvas.translate(offset.dx, offset.dy);
      canvas.rotate(angle);
      canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset.zero, width: side, height: side), const Radius.circular(3)), tile);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_BackdropPainter oldDelegate) => oldDelegate.p.isDark != p.isDark;
}

class _Panel extends StatelessWidget {
  const _Panel({required this.palette, required this.child, this.radius = AppRadius.md, this.padding = const EdgeInsets.all(12), this.elevated = true});

  final _Palette palette;
  final Widget child;
  final double radius;
  final EdgeInsets padding;
  final bool elevated;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: elevated ? palette.card : Color.alphaBlend(palette.tint, palette.card),
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: palette.cardBorder),
        boxShadow: elevated && !palette.isDark
            ? [BoxShadow(color: AppColors.navy.withValues(alpha: 0.08), blurRadius: 18, offset: const Offset(0, 8))]
            : null,
      ),
      child: child,
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.width, required this.color, this.height = 8});

  final double width;
  final double height;
  final Color color;

  @override
  Widget build(BuildContext context) =>
      Container(width: width, height: height, decoration: BoxDecoration(color: color, borderRadius: AppRadius.pillAll));
}

class _Pill extends StatelessWidget {
  const _Pill({required this.width, required this.color});

  final double width;
  final Color color;

  @override
  Widget build(BuildContext context) =>
      Container(width: width, height: 16, decoration: BoxDecoration(color: color, borderRadius: AppRadius.pillAll));
}

class _Badge extends StatelessWidget {
  const _Badge({required this.palette, required this.icon, required this.size, this.tone});

  final _Palette palette;
  final IconData icon;
  final double size;
  final Color? tone;

  @override
  Widget build(BuildContext context) {
    final color = tone ?? palette.primary;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: palette.isDark ? null : [BoxShadow(color: color.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))],
      ),
      child: Icon(icon, size: size * 0.52, color: palette.onPrimary),
    );
  }
}

class _Spark extends StatelessWidget {
  const _Spark({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) => CustomPaint(size: Size.square(size), painter: _SparkPainter(color));
}

class _SparkPainter extends CustomPainter {
  const _SparkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) => canvas.drawPath(sparkPath(size.center(Offset.zero), size.width / 2), Paint()..color = color);

  @override
  bool shouldRepaint(_SparkPainter oldDelegate) => oldDelegate.color != color;
}

/// Four-point star with concave sides — the CareerOS logo's spark.
Path sparkPath(Offset c, double r) {
  final k = r * 0.22;
  return Path()
    ..moveTo(c.dx, c.dy - r)
    ..quadraticBezierTo(c.dx + k, c.dy - k, c.dx + r, c.dy)
    ..quadraticBezierTo(c.dx + k, c.dy + k, c.dx, c.dy + r)
    ..quadraticBezierTo(c.dx - k, c.dy + k, c.dx - r, c.dy)
    ..quadraticBezierTo(c.dx - k, c.dy - k, c.dx, c.dy - r)
    ..close();
}

class _OpportunityRow extends StatelessWidget {
  const _OpportunityRow({required this.palette, required this.icon, required this.tone, this.saved = false});

  final _Palette palette;
  final IconData icon;
  final Color tone;
  final bool saved;

  @override
  Widget build(BuildContext context) {
    final p = palette;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(color: tone, borderRadius: AppRadius.mdAll),
          child: Icon(icon, size: 22, color: p.onPrimary),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 2),
              _Bar(width: 92, color: p.deep, height: 9),
              const SizedBox(height: 7),
              _Bar(width: 64, color: p.line),
              if (saved) ...[
                const SizedBox(height: 10),
                Row(children: [_Pill(width: 40, color: p.tint), const SizedBox(width: 6), _Pill(width: 30, color: p.tint)]),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _CheckDot extends StatelessWidget {
  const _CheckDot({required this.palette, required this.done});

  final _Palette palette;
  final bool done;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 20,
      height: 20,
      decoration: BoxDecoration(
        color: done ? palette.primary : null,
        shape: BoxShape.circle,
        border: done ? null : Border.all(color: palette.line, width: 2),
      ),
      child: done ? Icon(AppIcons.check, size: 14, color: palette.onPrimary) : null,
    );
  }
}

class _BubblePainter extends CustomPainter {
  const _BubblePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final body = RRect.fromRectAndRadius(Rect.fromLTWH(0, 0, size.width, size.height - 10), const Radius.circular(18));
    final tail = Path()
      ..moveTo(22, size.height - 12)
      ..lineTo(18, size.height)
      ..lineTo(38, size.height - 12)
      ..close();
    final paint = Paint()..color = color;
    canvas.drawRRect(body, paint);
    canvas.drawPath(tail, paint);
  }

  @override
  bool shouldRepaint(_BubblePainter oldDelegate) => oldDelegate.color != color;
}

class _RingPainter extends CustomPainter {
  const _RingPainter({required this.track, required this.value, required this.fraction});

  final Color track;
  final Color value;
  final double fraction;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final stroke = size.width * 0.12;
    final inner = rect.deflate(stroke / 2);
    canvas.drawArc(inner, 0, math.pi * 2, false, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..color = track);
    canvas.drawArc(inner, -math.pi / 2, math.pi * 2 * fraction, false, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..color = value);
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) => oldDelegate.value != value || oldDelegate.track != track;
}

enum _TimelineState { done, doneLater, current, upcoming }

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.palette, required this.state, required this.last});

  final _Palette palette;
  final _TimelineState state;
  final bool last;

  @override
  Widget build(BuildContext context) {
    final p = palette;
    final done = state == _TimelineState.done || state == _TimelineState.doneLater;
    final current = state == _TimelineState.current;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          width: 24,
          child: Column(
            children: [
              Container(
                width: 22,
                height: 22,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: done ? p.success : (current ? p.card : null),
                  border: done ? null : Border.all(color: current ? p.primary : p.line, width: current ? 5 : 2),
                ),
                child: done ? Icon(AppIcons.check, size: 14, color: p.onPrimary) : null,
              ),
              if (!last) Expanded(child: Container(width: 3, color: done ? p.success.withValues(alpha: 0.5) : p.line)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Align(
            alignment: Alignment.topLeft,
            child: Container(
              padding: current ? const EdgeInsets.symmetric(horizontal: 8, vertical: 6) : const EdgeInsets.only(top: 3),
              decoration: current ? BoxDecoration(color: p.tint, borderRadius: AppRadius.smAll) : null,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  _Bar(width: switch (state) { _TimelineState.done => 70, _TimelineState.doneLater => 86, _TimelineState.current => 96, _TimelineState.upcoming => 58 }, color: current ? p.primary : (done ? p.deep : p.line), height: 8),
                  const SizedBox(height: 5),
                  _Bar(width: 44, color: p.line, height: 6),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// --------------------------------------------------------------------------------------------------
// Climb: a person stepping up rising bars toward the spark, with a plant.
// --------------------------------------------------------------------------------------------------

class _ClimbPainter extends CustomPainter {
  const _ClimbPainter(this.p);

  final _Palette p;

  @override
  void paint(Canvas canvas, Size size) {
    const baseline = 228.0;

    // Ground.
    canvas.drawLine(
      const Offset(34, baseline),
      const Offset(300, baseline),
      Paint()
        ..color = p.line
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round,
    );

    // Rising bars with a lighter side face.
    const bars = [(140.0, 44.0), (182.0, 82.0), (224.0, 122.0), (266.0, 166.0)];
    for (final (x, h) in bars) {
      final rect = Rect.fromLTWH(x, baseline - h, 30, h);
      final body = RRect.fromRectAndCorners(rect, topLeft: const Radius.circular(6), topRight: const Radius.circular(6));
      canvas.drawRRect(
        body,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [p.primary, p.soft],
          ).createShader(rect),
      );
      canvas.drawRRect(
        RRect.fromRectAndCorners(Rect.fromLTWH(x + 21, baseline - h, 9, h), topRight: const Radius.circular(6)),
        Paint()..color = Colors.white.withValues(alpha: p.isDark ? 0.10 : 0.28),
      );
    }

    // Plant.
    final stem = Path()
      ..moveTo(92, baseline)
      ..quadraticBezierTo(96, 190, 86, 146);
    canvas.drawPath(
      stem,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round
        ..color = p.deep,
    );
    _leaf(canvas, const Offset(70, 170), 22, 44, -0.5, p.primary);
    _leaf(canvas, const Offset(108, 160), 18, 38, 0.55, p.deep);
    _leaf(canvas, const Offset(84, 128), 14, 30, -0.1, p.soft);
    _leaf(canvas, const Offset(64, 210), 12, 24, -0.9, p.soft);

    // Person, stepping from the second bar onto the third.
    final limb = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    const hip = Offset(214, 104);
    const shoulder = Offset(222, 66);

    // Back leg on bar 2 (top at y = 146).
    canvas.drawPath(
      Path()
        ..moveTo(hip.dx, hip.dy)
        ..lineTo(204, 126)
        ..lineTo(198, 144),
      limb
        ..strokeWidth = 11
        ..color = p.deep,
    );
    _shoe(canvas, const Offset(200, 146), p.deep);

    // Front leg lifted onto bar 3 (top at y = 106).
    canvas.drawPath(
      Path()
        ..moveTo(hip.dx, hip.dy)
        ..lineTo(236, 90)
        ..lineTo(240, 104),
      limb
        ..strokeWidth = 11
        ..color = p.deep,
    );
    _shoe(canvas, const Offset(243, 106), p.deep);

    // Back arm.
    canvas.drawPath(
      Path()
        ..moveTo(shoulder.dx, shoulder.dy + 4)
        ..lineTo(206, 82)
        ..lineTo(198, 96),
      limb
        ..strokeWidth = 8
        ..color = p.primary,
    );

    // Torso.
    canvas.drawLine(
      hip,
      shoulder,
      Paint()
        ..strokeWidth = 18
        ..strokeCap = StrokeCap.round
        ..color = p.primary,
    );

    // Reaching arm, toward the spark.
    canvas.drawPath(
      Path()
        ..moveTo(shoulder.dx + 2, shoulder.dy)
        ..lineTo(238, 50)
        ..lineTo(250, 30),
      limb
        ..strokeWidth = 8
        ..color = p.primary,
    );

    // Head.
    canvas.drawCircle(const Offset(226, 42), 11, Paint()..color = p.deep);

    // Sparks.
    canvas.drawPath(sparkPath(const Offset(276, 26), 15), Paint()..color = p.accent);
    canvas.drawPath(sparkPath(const Offset(300, 58), 7), Paint()..color = p.primary);
    canvas.drawPath(sparkPath(const Offset(44, 62), 9), Paint()..color = p.soft);
  }

  void _leaf(Canvas canvas, Offset center, double width, double height, double angle, Color color) {
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(angle);
    final leaf = Path()
      ..moveTo(0, -height / 2)
      ..quadraticBezierTo(width, 0, 0, height / 2)
      ..quadraticBezierTo(-width, 0, 0, -height / 2)
      ..close();
    canvas.drawPath(leaf, Paint()..color = color);
    canvas.restore();
  }

  void _shoe(Canvas canvas, Offset toe, Color color) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTWH(toe.dx - 9, toe.dy - 6, 18, 7), const Radius.circular(4)),
      Paint()..color = color,
    );
  }

  @override
  bool shouldRepaint(_ClimbPainter oldDelegate) => oldDelegate.p.isDark != p.isDark;
}
