import "package:flutter/material.dart";

import "../../../theme/app_colors.dart";
import "../data/application_models.dart";

Color stageColor(ApplicationStage stage) {
  switch (stage) {
    case ApplicationStage.hired:
    case ApplicationStage.offer:
      return AppColors.success;
    case ApplicationStage.rejected:
    case ApplicationStage.withdrawn:
    case ApplicationStage.expired:
      return AppColors.danger;
    case ApplicationStage.interview:
    case ApplicationStage.finalInterview:
    case ApplicationStage.assessmentCentre:
    case ApplicationStage.aptitudeTest:
    case ApplicationStage.medical:
    case ApplicationStage.backgroundCheck:
      return AppColors.warning;
    case ApplicationStage.noResponse:
      return AppColors.muted;
    default:
      return AppColors.blue;
  }
}

class StageBadge extends StatelessWidget {
  const StageBadge({super.key, required this.stage});

  final ApplicationStage stage;

  @override
  Widget build(BuildContext context) {
    final color = stageColor(stage);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
      child: Text(stage.label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
