import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "aptitude_providers.dart";

Future<void> showQuestionNavigatorSheet(BuildContext context, {required String sessionId}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => _QuestionNavigatorSheet(sessionId: sessionId),
  );
}

/// Question Navigator (spec §17): shows every question's state at a glance — current, answered,
/// unanswered, flagged — and jumps to it on tap.
class _QuestionNavigatorSheet extends ConsumerWidget {
  const _QuestionNavigatorSheet({required this.sessionId});

  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final examState = ref.watch(examControllerProvider(sessionId));
    final controller = ref.read(examControllerProvider(sessionId).notifier);
    final session = examState.session;

    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      minChildSize: 0.4,
      maxChildSize: 0.9,
      expand: false,
      builder: (context, scrollController) => Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, 0, AppSpacing.pageH, AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Question Navigator", style: context.text.titleLarge),
            Gap.sm,
            const _Legend(),
            Gap.md,
            Expanded(
              child: session == null
                  ? const SizedBox.shrink()
                  : GridView.builder(
                      controller: scrollController,
                      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent: 64,
                        mainAxisSpacing: AppSpacing.xs,
                        crossAxisSpacing: AppSpacing.xs,
                      ),
                      itemCount: session.questions.length,
                      itemBuilder: (context, index) {
                        final question = session.questions[index];
                        return _NavigatorCell(
                          index: index,
                          isCurrent: index == examState.currentIndex,
                          isAnswered: question.isAnswered,
                          isFlagged: question.isFlagged,
                          onTap: () {
                            controller.goToQuestion(index);
                            Navigator.of(context).pop();
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.md,
      runSpacing: AppSpacing.xs,
      children: [
        _LegendItem(color: context.colors.primary, label: "Current"),
        const _LegendItem(color: AppColors.success, label: "Answered", icon: Icons.check),
        _LegendItem(color: context.colors.border, label: "Unanswered"),
        const _LegendItem(color: AppColors.warning, label: "Flagged", icon: Icons.outlined_flag),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label, this.icon});

  final Color color;
  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          child: icon != null ? Icon(icon, size: 11, color: Colors.white) : null,
        ),
        const SizedBox(width: 6),
        Text(label, style: context.text.bodySmall),
      ],
    );
  }
}

class _NavigatorCell extends StatelessWidget {
  const _NavigatorCell({
    required this.index,
    required this.isCurrent,
    required this.isAnswered,
    required this.isFlagged,
    required this.onTap,
  });

  final int index;
  final bool isCurrent;
  final bool isAnswered;
  final bool isFlagged;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final Color background;
    final Color foreground;
    Border? border;
    if (isCurrent) {
      background = colors.primary;
      foreground = Colors.white;
    } else if (isFlagged) {
      background = AppTone.warning.tint(context);
      foreground = AppTone.warning.onTint(context);
    } else if (isAnswered) {
      background = AppTone.success.tint(context);
      foreground = AppTone.success.onTint(context);
    } else {
      background = colors.surface;
      foreground = colors.textSecondary;
      border = Border.all(color: colors.border);
    }

    final state = [
      if (isCurrent) "current",
      isAnswered ? "answered" : "unanswered",
      if (isFlagged) "flagged",
    ].join(", ");

    return Semantics(
      button: true,
      label: "Question ${index + 1}, $state",
      excludeSemantics: true,
      child: Material(
        color: background,
        shape: RoundedRectangleBorder(borderRadius: AppRadius.mdAll, side: border?.top ?? BorderSide.none),
        child: InkWell(
          borderRadius: AppRadius.mdAll,
          onTap: onTap,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Text("${index + 1}", style: context.text.labelLarge?.copyWith(color: foreground)),
              if (isFlagged && !isCurrent)
                const Positioned(top: 4, right: 4, child: Icon(Icons.outlined_flag, size: 12, color: AppColors.warning)),
            ],
          ),
        ),
      ),
    );
  }
}
