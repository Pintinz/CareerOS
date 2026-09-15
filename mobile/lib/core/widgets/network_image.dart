import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";

import "../../config/env.dart";
import "../design/design.dart";

/// Images uploaded to a local development backend are addressed as `localhost`, which on an
/// Android emulator or a phone is the device itself. Point such URLs at the host the API client
/// already uses (e.g. 10.0.2.2); real deployment URLs are returned unchanged.
String resolveMediaUrl(String url, {String apiBaseUrl = Env.apiBaseUrl}) {
  final media = Uri.tryParse(url);
  final api = Uri.tryParse(apiBaseUrl);
  if (media == null || api == null || api.host.isEmpty) return url;
  const loopback = {"localhost", "127.0.0.1"};
  if (!loopback.contains(media.host) || loopback.contains(api.host)) return url;
  return media.replace(scheme: api.scheme, host: api.host, port: api.port).toString();
}

/// Cached network image (logos, thumbnails) with an initials or icon fallback while loading,
/// when the URL is missing, or when the image fails.
class NetworkImageWithFallback extends StatelessWidget {
  const NetworkImageWithFallback({
    super.key,
    required this.url,
    required this.fallbackText,
    this.fallbackIcon,
    this.size = 48,
    this.width,
    this.height,
    this.radius,
    this.tone = AppTone.primary,
    this.fit = BoxFit.cover,
  });

  final String? url;

  /// Name used for the initial when no image is available.
  final String fallbackText;
  final IconData? fallbackIcon;
  final double size;
  final double? width;
  final double? height;
  final double? radius;
  final AppTone tone;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final w = width ?? size;
    final h = height ?? size;
    final r = BorderRadius.circular(radius ?? (w < 64 ? w * 0.28 : AppRadius.card));
    final initial = fallbackText.trim().isNotEmpty ? fallbackText.trim()[0].toUpperCase() : "?";

    final fallback = Container(
      width: w,
      height: h,
      decoration: BoxDecoration(color: tone.tint(context), borderRadius: r),
      alignment: Alignment.center,
      child: fallbackIcon != null
          ? Icon(fallbackIcon, color: tone.color(context), size: w * 0.46)
          : Text(
              initial,
              style: context.text.titleLarge?.copyWith(color: tone.color(context), fontSize: w * 0.4),
            ),
    );

    if (url == null || url!.isEmpty) return ExcludeSemantics(child: fallback);

    return ExcludeSemantics(
      child: ClipRRect(
        borderRadius: r,
        child: CachedNetworkImage(
          imageUrl: resolveMediaUrl(url!),
          width: w,
          height: h,
          fit: fit,
          memCacheWidth: (w * MediaQuery.devicePixelRatioOf(context)).round(),
          placeholder: (_, __) => fallback,
          errorWidget: (_, __, ___) => fallback,
        ),
      ),
    );
  }
}
