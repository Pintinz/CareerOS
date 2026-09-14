import "package:flutter/material.dart";

import "../design/design.dart";

/// Official CareerOS brand artwork: the C with a rising ribbon arrow and spark, and the
/// "Career" + "OS" wordmark. Cut from the owner-supplied brand board
/// (`.claude/skills/careeros-ui-system/assets/brand-reference/careeros-brand-board.png`) by
/// `tool/generate_brand_assets.py` — regenerate there, never edit the PNGs by hand.
abstract final class CareerOSBrandAssets {
  static const symbol = "assets/brand/careeros_symbol.png";
  static const symbolOnDark = "assets/brand/careeros_symbol_on_dark.png";
  static const wordmark = "assets/brand/careeros_wordmark.png";
  static const wordmarkOnDark = "assets/brand/careeros_wordmark_on_dark.png";

  /// Width ÷ height of the cut-outs.
  static const symbolAspect = 522 / 457;
  static const wordmarkAspect = 795 / 136;
}

/// The CareerOS symbol, fitted inside a `size` × `size` box.
class CareerOSMark extends StatelessWidget {
  const CareerOSMark({super.key, this.size = 40, this.onDark, this.decorative = false});

  final double size;

  /// On-dark variant (white C) for navy/dark grounds. Defaults to the current theme's brightness.
  final bool? onDark;

  /// True when a wordmark or title next to it already names CareerOS (avoids a double announcement).
  final bool decorative;

  @override
  Widget build(BuildContext context) {
    final reversed = onDark ?? context.colors.isDark;
    return _BrandImage(
      asset: reversed ? CareerOSBrandAssets.symbolOnDark : CareerOSBrandAssets.symbol,
      width: size,
      height: size,
      semanticLabel: decorative ? null : "CareerOS",
    );
  }
}

/// "Career" in navy + "OS" in blue (white "Career" on dark grounds), `height` tall.
class CareerOSWordmark extends StatelessWidget {
  const CareerOSWordmark({super.key, this.height = 24, this.onDark});

  final double height;
  final bool? onDark;

  @override
  Widget build(BuildContext context) {
    final reversed = onDark ?? context.colors.isDark;
    return _BrandImage(
      asset: reversed ? CareerOSBrandAssets.wordmarkOnDark : CareerOSBrandAssets.wordmark,
      width: height * CareerOSBrandAssets.wordmarkAspect,
      height: height,
      semanticLabel: "CareerOS",
    );
  }
}

/// Horizontal primary logo: symbol + wordmark, proportioned like the brand board's primary lockup
/// (wordmark ≈ 0.41× the symbol height, sitting on the symbol's lower half).
class CareerOSLogo extends StatelessWidget {
  const CareerOSLogo({super.key, this.markSize = 36, this.onDark});

  /// Symbol height.
  final double markSize;
  final bool? onDark;

  @override
  Widget build(BuildContext context) {
    final reversed = onDark ?? context.colors.isDark;
    final symbolWidth = markSize * CareerOSBrandAssets.symbolAspect;
    final wordmarkHeight = markSize * 0.41;
    final wordmarkWidth = wordmarkHeight * CareerOSBrandAssets.wordmarkAspect;
    // On the board the wordmark starts just under the spark's tip, so it overlaps the symbol's box.
    final wordmarkLeft = symbolWidth - markSize * 0.046;
    return Semantics(
      label: "CareerOS",
      image: true,
      excludeSemantics: true,
      child: SizedBox(
        width: wordmarkLeft + wordmarkWidth,
        height: markSize,
        child: Stack(
          children: [
            _BrandImage(
              asset: reversed ? CareerOSBrandAssets.symbolOnDark : CareerOSBrandAssets.symbol,
              width: symbolWidth,
              height: markSize,
            ),
            Positioned(
              left: wordmarkLeft,
              top: markSize * 0.37,
              child: _BrandImage(
                asset: reversed ? CareerOSBrandAssets.wordmarkOnDark : CareerOSBrandAssets.wordmark,
                width: wordmarkWidth,
                height: wordmarkHeight,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandImage extends StatelessWidget {
  const _BrandImage({required this.asset, required this.width, required this.height, this.semanticLabel});

  final String asset;
  final double width;
  final double height;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      asset,
      width: width,
      height: height,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
      semanticLabel: semanticLabel,
      excludeFromSemantics: semanticLabel == null,
      // Never let a missing asset take a screen down; keep the layout box.
      errorBuilder: (_, __, ___) => SizedBox(width: width, height: height),
    );
  }
}
