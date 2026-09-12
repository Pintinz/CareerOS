import "package:flutter/material.dart";

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

  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text("Submit Test?"),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Answered: $answered"),
          Text("Unanswered: $unanswered"),
          Text("Flagged: $flagged"),
          if (remainingLabel != null) ...[
            const SizedBox(height: 8),
            Text(remainingLabel, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 12),
          const Text("Once submitted, you cannot change your answers."),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Continue Test")),
        FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Submit")),
      ],
    ),
  );
}
