import "package:flutter/material.dart";

import "../design/design.dart";
import "../utils/date_labels.dart";

/// Whether a listing can still be applied to, as established by the backend from its source
/// (backend `app/services/availability.py`). Feeds only return active listings; saved items and
/// tracked applications can still open the others.
enum OpportunityAvailability {
  active,
  expired,
  closed,
  unavailable;

  static OpportunityAvailability fromApi(String? value) => switch (value) {
        "EXPIRED" => OpportunityAvailability.expired,
        "CLOSED" => OpportunityAvailability.closed,
        "UNAVAILABLE" => OpportunityAvailability.unavailable,
        _ => OpportunityAvailability.active,
      };

  bool get isActive => this == OpportunityAvailability.active;

  /// Only a listing that still exists at its source is worth opening there.
  bool get sourceStillMeaningful => this != OpportunityAvailability.unavailable;

  String get shortLabel => switch (this) {
        OpportunityAvailability.active => "Open",
        OpportunityAvailability.expired => "Expired",
        OpportunityAvailability.closed => "Closed",
        OpportunityAvailability.unavailable => "Unavailable",
      };

  AppTone get tone => switch (this) {
        OpportunityAvailability.active => AppTone.success,
        OpportunityAvailability.expired => AppTone.neutral,
        OpportunityAvailability.closed => AppTone.warning,
        OpportunityAvailability.unavailable => AppTone.danger,
      };
}

/// Explains why a listing can't be applied to. Renders nothing for active listings.
class AvailabilityNotice extends StatelessWidget {
  const AvailabilityNotice({super.key, required this.availability});

  final OpportunityAvailability availability;

  @override
  Widget build(BuildContext context) {
    if (availability.isActive) return const SizedBox.shrink();
    final (icon, title, message) = switch (availability) {
      OpportunityAvailability.expired => (
          Icons.event_busy_outlined,
          "Expired",
          "This opportunity is no longer active on CareerOS.",
        ),
      OpportunityAvailability.closed => (
          Icons.do_not_disturb_on_outlined,
          "Applications closed",
          "The official listing says applications are closed.",
        ),
      _ => (
          Icons.link_off_rounded,
          "Listing unavailable",
          "CareerOS could not confirm that this opportunity is still open.",
        ),
    };
    final tone = availability.tone;
    return Semantics(
      container: true,
      label: "$title. $message",
      excludeSemantics: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.sm),
        decoration: BoxDecoration(color: tone.tint(context), borderRadius: AppRadius.mdAll),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 20, color: tone.onTint(context)),
            Gap.xs,
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: context.text.titleSmall?.copyWith(color: tone.onTint(context))),
                  const SizedBox(height: 2),
                  Text(message, style: context.text.bodyMedium?.copyWith(color: context.colors.textPrimary)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// A quiet provenance line for detail screens: "Official source · Last verified 2d ago". Shows
/// nothing unless the backend marked the listing as coming from an official organization channel.
class SourceProvenance extends StatelessWidget {
  const SourceProvenance({super.key, required this.isOfficialSource, this.lastVerifiedAt});

  final bool isOfficialSource;
  final DateTime? lastVerifiedAt;

  @override
  Widget build(BuildContext context) {
    if (!isOfficialSource) return const SizedBox.shrink();
    final verified = lastVerifiedAt;
    final label = verified == null ? "Official source" : "Official source · Last verified ${DateLabels.published(verified).toLowerCase()}";
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(AppIcons.verified, size: 14, color: AppColors.success),
        const SizedBox(width: 4),
        Flexible(child: Text(label, style: context.text.bodySmall)),
      ],
    );
  }
}

/// Enum values the backend uses when a source doesn't state a fact; never shown as a label.
bool isStatedValue(String? value) => value != null && value.isNotEmpty && value != "UNSPECIFIED";
