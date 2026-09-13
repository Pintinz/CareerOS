import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../data/application_models.dart";

/// Semantic tone per recruitment stage (design-tokens: Saved gray · Applied blue · Screening cyan ·
/// Assessment purple · Interview amber · Offer green · Rejected red).
AppTone stageTone(ApplicationStage stage) => switch (stage) {
      ApplicationStage.saved => AppTone.neutral,
      ApplicationStage.applied => AppTone.primary,
      ApplicationStage.applicationReceived ||
      ApplicationStage.underReview ||
      ApplicationStage.shortlisted ||
      ApplicationStage.recruiterScreen =>
        AppTone.info,
      ApplicationStage.aptitudeTest ||
      ApplicationStage.assessmentCompleted ||
      ApplicationStage.assessmentCentre =>
        AppTone.purple,
      ApplicationStage.interview || ApplicationStage.finalInterview => AppTone.warning,
      ApplicationStage.backgroundCheck ||
      ApplicationStage.medical ||
      ApplicationStage.offer ||
      ApplicationStage.hired =>
        AppTone.success,
      ApplicationStage.rejected => AppTone.danger,
      ApplicationStage.withdrawn || ApplicationStage.expired || ApplicationStage.noResponse => AppTone.neutral,
    };

IconData stageIcon(ApplicationStage stage) => switch (stage) {
      ApplicationStage.saved => AppIcons.saved,
      ApplicationStage.applied || ApplicationStage.applicationReceived => Icons.send_rounded,
      ApplicationStage.underReview || ApplicationStage.shortlisted || ApplicationStage.recruiterScreen => Icons.manage_search_rounded,
      ApplicationStage.aptitudeTest || ApplicationStage.assessmentCompleted || ApplicationStage.assessmentCentre => AppIcons.aptitude,
      ApplicationStage.interview || ApplicationStage.finalInterview => AppIcons.interview,
      ApplicationStage.backgroundCheck || ApplicationStage.medical => Icons.fact_check_outlined,
      ApplicationStage.offer || ApplicationStage.hired => Icons.celebration_outlined,
      ApplicationStage.rejected => Icons.close_rounded,
      ApplicationStage.withdrawn || ApplicationStage.expired || ApplicationStage.noResponse => Icons.remove_circle_outline_rounded,
    };

/// Stage status pill — text + icon, so the stage never relies on color alone.
class StageBadge extends StatelessWidget {
  const StageBadge({super.key, required this.stage, this.dense = false});

  final ApplicationStage stage;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    return StatusChip(label: stage.label, tone: stageTone(stage), icon: stageIcon(stage), dense: dense);
  }
}
