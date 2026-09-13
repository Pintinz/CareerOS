import "package:flutter/material.dart";

import "../design/design.dart";
import "app_buttons.dart";

/// Modal bottom sheet with CareerOS chrome (drag handle, 24 px top radius, safe-area padding).
Future<T?> showCareerBottomSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  String? title,
  bool isScrollControlled = true,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: isScrollControlled,
    useSafeArea: true,
    builder: (sheetContext) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(sheetContext).bottom),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, 0, AppSpacing.pageH, AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (title != null) ...[
                Text(title, style: sheetContext.text.titleLarge),
                Gap.md,
              ],
              Flexible(child: builder(sheetContext)),
            ],
          ),
        ),
      ),
    ),
  );
}

/// Confirmation dialog. Returns `true` only when the confirm action is chosen.
Future<bool> showCareerDialog({
  required BuildContext context,
  required String title,
  required String message,
  required String confirmLabel,
  String cancelLabel = "Cancel",
  bool destructive = false,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actionsPadding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.lg),
      actions: [
        Row(
          children: [
            Expanded(
              child: AppOutlineButton(label: cancelLabel, onPressed: () => Navigator.of(dialogContext).pop(false)),
            ),
            Gap.sm,
            Expanded(
              child: destructive
                  ? DangerButton(label: confirmLabel, onPressed: () => Navigator.of(dialogContext).pop(true))
                  : PrimaryButton(label: confirmLabel, onPressed: () => Navigator.of(dialogContext).pop(true)),
            ),
          ],
        ),
      ],
    ),
  );
  return result ?? false;
}
