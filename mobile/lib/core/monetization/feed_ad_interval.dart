/// Pure helper (spec §12): decides which list positions get an ad slot inserted, given a
/// content-item count and a configurable interval — e.g. interval=6 inserts an ad slot after
/// items 6, 12, 18, ... A slot is never inserted before the first `interval` items, and never
/// after the very last item (no trailing ad with nothing following it).
///
/// Deliberately not hardcoded per-screen (spec: "Do not hardcode repeatedly across screens") —
/// every feed that wants ad slots calls this with its own item count and the shared
/// `MonetizationConfig.feedAdInterval`.
List<int> adSlotPositionsForFeed({required int itemCount, required int interval}) {
  if (interval <= 0 || itemCount <= interval) return const [];
  final positions = <int>[];
  for (var afterItem = interval; afterItem < itemCount; afterItem += interval) {
    positions.add(afterItem);
  }
  return positions;
}
