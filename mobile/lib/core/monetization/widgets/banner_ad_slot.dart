import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:google_mobile_ads/google_mobile_ads.dart";

import "../../design/design.dart";
import "../ad_placement.dart";
import "../monetization_providers.dart";

/// An anchored adaptive banner slot (spec §11) for feeds/browse surfaces only. On any failure —
/// disabled, Pro user, load error — this collapses to nothing (`SizedBox.shrink`), never a blank
/// fixed-height container, a stuck spinner, or a layout hole (spec §13). Content around it stays
/// fully usable either way.
class BannerAdSlot extends ConsumerStatefulWidget {
  const BannerAdSlot({super.key, required this.placement});

  final AdPlacement placement;

  @override
  ConsumerState<BannerAdSlot> createState() => _BannerAdSlotState();
}

class _BannerAdSlotState extends ConsumerState<BannerAdSlot> {
  BannerAd? _ad;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final adService = ref.read(adServiceProvider);
    // Feeds pad the page and this slot pads its label container — request a banner that fits the
    // space it actually gets, or the platform view overflows horizontally.
    final width = (MediaQuery.sizeOf(context).width - AppSpacing.pageH * 2 - AppSpacing.sm * 2).truncate();
    final size = await AdSize.getLargeAnchoredAdaptiveBannerAdSize(width) ?? AdSize.banner;
    final ad = await adService.loadBanner(placement: widget.placement, size: size);
    if (!mounted) {
      ad?.dispose();
      return;
    }
    setState(() {
      _ad = ad;
      _loading = false;
    });
  }

  @override
  void dispose() {
    _ad?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ad = _ad;
    if (_loading || ad == null) return const SizedBox.shrink();
    final colors = context.colors;
    // Advertising label + muted ground (spec §41-42, ux-rules.md): a banner must never sit
    // unlabeled among job/scholarship cards where it could be mistaken for CareerOS content, and it
    // is deliberately not styled like a content card.
    return Semantics(
      container: true,
      label: "Advertisement",
      child: Container(
        padding: const EdgeInsets.fromLTRB(AppSpacing.sm, AppSpacing.xs, AppSpacing.sm, AppSpacing.sm),
        decoration: BoxDecoration(color: colors.surfaceMuted, borderRadius: AppRadius.mdAll),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
                child: Text("Advertisement", style: context.text.labelSmall),
              ),
            ),
            SizedBox(
              width: ad.size.width.toDouble(),
              height: ad.size.height.toDouble(),
              child: AdWidget(ad: ad),
            ),
          ],
        ),
      ),
    );
  }
}
