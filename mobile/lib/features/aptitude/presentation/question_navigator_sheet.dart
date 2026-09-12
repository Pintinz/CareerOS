import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../theme/app_colors.dart";
import "aptitude_providers.dart";

Future<void> showQuestionNavigatorSheet(BuildContext context, {required String sessionId}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
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
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Question Navigator", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            const _Legend(),
            const SizedBox(height: 16),
            Expanded(
              child: session == null
                  ? const SizedBox.shrink()
                  : GridView.builder(
                      controller: scrollController,
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 5,
                        mainAxisSpacing: 10,
                        crossAxisSpacing: 10,
                      ),
                      itemCount: session.questions.length,
                      itemBuilder: (context, index) {
                        final question = session.questions[index];
                        final isCurrent = index == examState.currentIndex;
                        return _NavigatorCell(
                          index: index,
                          isCurrent: isCurrent,
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
    return const Wrap(
      spacing: 16,
      runSpacing: 8,
      children: [
        _LegendItem(color: AppColors.blue, label: "Current"),
        _LegendItem(color: AppColors.success, label: "Answered", icon: Icons.check),
        _LegendItem(color: AppColors.muted, label: "Unanswered"),
        _LegendItem(color: AppColors.warning, label: "Flagged", icon: Icons.flag),
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
          width: 14,
          height: 14,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          child: icon != null ? Icon(icon, size: 10, color: Colors.white) : null,
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.muted)),
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
    final Color background;
    final Color foreground;
    if (isCurrent) {
      background = AppColors.blue;
      foreground = Colors.white;
    } else if (isFlagged) {
      background = AppColors.warning.withValues(alpha: 0.15);
      foreground = AppColors.warning;
    } else if (isAnswered) {
      background = AppColors.success.withValues(alpha: 0.15);
      foreground = AppColors.success;
    } else {
      background = AppColors.background;
      foreground = AppColors.muted;
    }

    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(10)),
        alignment: Alignment.center,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Text("${index + 1}", style: TextStyle(color: foreground, fontWeight: FontWeight.w600)),
            if (isFlagged && !isCurrent)
              const Positioned(top: 2, right: 2, child: Icon(Icons.flag, size: 10, color: AppColors.warning)),
          ],
        ),
      ),
    );
  }
}
