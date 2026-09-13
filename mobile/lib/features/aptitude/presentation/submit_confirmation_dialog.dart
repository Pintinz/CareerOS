import "package:flutter/material.dart";

import "../../../core/design/design.dart";

/// Submit confirmation dialog (spec §17): shows Answered/Unanswered/Flagged counts and the time
/// remaining before letting the user commit. If time has already expired, the caller submits
/// directly without ever showing this dialog.
Future<bool?> showSubmitConfirmationDialog(
  BuildContext context, {
  required int answered,
  required int unanswered,
  required int flagged,
  int? remainingSeconds,
}) {
  String? remainingLabel;
  if (remainingSeconds != null) {
    final minutes = remainingSeconds ~/ 60;
    final seconds = remainingSeconds % 60;
    remainingLabel = "${minutes}m ${seconds}s remaining";
  }

  Widget row(BuildContext context, IconData icon, Color color, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            Icon(icon, size: 18, color: color),
            Gap.xs,
            Text(text, style: context.text.bodyLarge),
          ],
        ),
      );

  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text("Submit Test?"),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          row(context, Icons.check_circle_outline_rounded, AppColors.success, "Answered: $answered"),
          row(context, Icons.radio_button_unchecked_rounded, context.colors.textSecondary, "Unanswered: $unanswered"),
          row(context, Icons.flag_rounded, AppColors.warning, "Flagged: $flagged"),
          if (remainingLabel != null) ...[
            Gap.xs,
            Text(remainingLabel, style: context.text.titleSmall),
          ],
          Gap.sm,
          Text("Once submitted, you cannot change your answers.", style: context.text.bodyMedium),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Continue Test")),
        FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Submit")),
      ],
    ),
  );
}
