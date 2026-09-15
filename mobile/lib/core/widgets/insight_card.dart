import "package:flutter/material.dart";

import "../design/design.dart";
import "icon_tile.dart";

/// Attention/insight card: recruitment updates, upcoming stages, next actions, honest notices.
/// Same surface as [CareerCard]; the tone lives in the icon and the action rather than a colored
/// edge rail. One action at most. On narrow or large-text layouts the action moves below the text
/// instead of squeezing it.
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
    final hasAction = actionLabel != null && onAction != null;
    final actionColor = tone == AppTone.neutral ? colors.primary : tone.onTint(context);

    Widget actionButton({required bool inline}) => TextButton(
          onPressed: onAction,
          style: TextButton.styleFrom(
            foregroundColor: actionColor,
            padding: EdgeInsets.symmetric(horizontal: inline ? AppSpacing.sm : 0),
            minimumSize: const Size(48, 40),
            textStyle: context.text.labelMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(child: Text(actionLabel!, maxLines: 1, overflow: TextOverflow.ellipsis)),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward_rounded, size: 16),
            ],
          ),
        );

    return LayoutBuilder(
      builder: (context, constraints) {
        final textScale = MediaQuery.textScalerOf(context).scale(1);
        // Long action labels or narrow/large-text layouts put the action under the text.
        final stacked = hasAction && (actionLabel!.length > 8 || constraints.maxWidth / textScale < 290);
        return DecoratedBox(
          decoration: BoxDecoration(borderRadius: AppRadius.cardAll, boxShadow: AppShadows.card(context)),
          child: Material(
            color: colors.surface,
            shape: RoundedRectangleBorder(borderRadius: AppRadius.cardAll, side: BorderSide(color: colors.border)),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: onTap ?? onAction,
              child: Padding(
                padding: EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, hasAction && !stacked ? AppSpacing.xxs : AppSpacing.md, stacked ? AppSpacing.xs : AppSpacing.md),
                child: Row(
                  crossAxisAlignment: stacked ? CrossAxisAlignment.start : CrossAxisAlignment.center,
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
                          if (stacked) Padding(padding: const EdgeInsets.only(top: 2), child: actionButton(inline: false)),
                        ],
                      ),
                    ),
                    if (hasAction && !stacked) actionButton(inline: true),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
