import "package:flutter/material.dart";

import "../design/design.dart";

/// Tinted rounded square holding an icon — the standard leading visual for rows, stats and areas.
class IconTile extends StatelessWidget {
  const IconTile({super.key, required this.icon, this.tone = AppTone.primary, this.size = 44, this.circle = false});

  final IconData icon;
  final AppTone tone;
  final double size;
  final bool circle;

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: tone.tint(context),
          shape: circle ? BoxShape.circle : BoxShape.rectangle,
          borderRadius: circle ? null : BorderRadius.circular(size * 0.3),
        ),
        alignment: Alignment.center,
        child: Icon(icon, color: tone.color(context), size: size * 0.5),
      ),
    );
  }
}
