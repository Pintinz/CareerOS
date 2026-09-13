import "package:flutter/material.dart";

import "../design/design.dart";
import "icon_tile.dart";

/// Attention/insight row with a tone accent rail: recruitment updates, upcoming stages, next
/// actions, honest notices. One action at most. On narrow or large-text layouts the action moves
/// below the text instead of squeezing it.
class InsightCard extends StatelessWidget {
  const InsightCard({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.messageWidget,
    this.tone = AppTone.primary,
    this.actionLabel,
    this.onAction,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String? message;

  /// Richer subtitle (e.g. an async-resolved company name). Shown below [message] when both exist.
  final Widget? messageWidget;
  final AppTone tone;
  final String? actionLabel;
  final VoidCallback? onAction;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final accent = tone.color(context);
    final hasAction = actionLabel != null && onAction != null;

    Widget actionButton() => TextButton(
          onPressed: onAction,
          style: TextButton.styleFrom(foregroundColor: tone.onTint(context)),
          child: Text(actionLabel!),
        );

    // LayoutBuilder must sit outside IntrinsicHeight (it can't report intrinsic sizes).
    return LayoutBuilder(
      builder: (context, constraints) {
        final textScale = MediaQuery.textScalerOf(context).scale(1);
        // Long action labels or narrow/large-text layouts put the action under the text.
        final stacked = hasAction && (actionLabel!.length > 8 || constraints.maxWidth / textScale < 290);
        return Material(
          color: colors.surface,
          shape: RoundedRectangleBorder(borderRadius: AppRadius.cardAll, side: BorderSide(color: colors.border)),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap ?? onAction,
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(width: 4, color: accent),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(AppSpacing.sm, AppSpacing.sm, AppSpacing.xs, AppSpacing.sm),
                      child: Row(
                        children: [
                          IconTile(icon: icon, tone: tone, size: 40, circle: true),
                          Gap.sm,
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(title, style: context.text.titleSmall),
                                if (message != null) ...[
                                  const SizedBox(height: 2),
                                  Text(message!, style: context.text.bodySmall),
                                ],
                                if (messageWidget != null) messageWidget!,
                                if (stacked)
                                  Padding(
                                    padding: const EdgeInsets.only(top: AppSpacing.xxs),
                                    child: Transform.translate(offset: const Offset(-AppSpacing.sm, 0), child: actionButton()),
                                  ),
                              ],
                            ),
                          ),
                          if (hasAction && !stacked) actionButton(),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
