import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:google_mobile_ads/google_mobile_ads.dart";

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
    final width = MediaQuery.sizeOf(context).width.truncate();
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
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Advertising label (spec §41-42): never let a banner sit unlabeled among job/scholarship
        // cards where it could be mistaken for CareerOS content.
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text(
            "Advertisement",
            style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Theme.of(context).hintColor),
          ),
        ),
        SizedBox(
          width: ad.size.width.toDouble(),
          height: ad.size.height.toDouble(),
          child: AdWidget(ad: ad),
        ),
      ],
    );
  }
}
