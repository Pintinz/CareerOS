import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";

/// Post-submission review (spec §17-18): shows every question with the user's answer, the
/// correct answer, and the explanation. Only reachable after a session is submitted — the
/// backend itself refuses to serve review data before then (409), so this screen never even
/// gets a chance to leak answers early.
class QuestionReviewScreen extends ConsumerStatefulWidget {
  const QuestionReviewScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  ConsumerState<QuestionReviewScreen> createState() => _QuestionReviewScreenState();
}

class _QuestionReviewScreenState extends ConsumerState<QuestionReviewScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final reviewAsync = ref.watch(sessionReviewProvider(widget.sessionId));

    return Scaffold(
      appBar: AppBar(title: const Text("Review Answers")),
      body: reviewAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorState(
          title: "We couldn't load your review",
          message: e.userMessage,
          onRetry: () => ref.invalidate(sessionReviewProvider(widget.sessionId)),
        ),
        data: (review) {
          if (review.questions.isEmpty) {
            return const EmptyState(
              icon: AppIcons.aptitude,
              title: "No questions to review",
              message: "This session didn't include any questions.",
            );
          }
          final total = review.questions.length;
          final question = review.questions[_index.clamp(0, total - 1)];
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xxs, AppSpacing.pageH, AppSpacing.sm),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text("Question ${_index + 1} of $total", style: context.text.titleSmall),
                    Gap.xs,
                    CareerProgressBar(value: (_index + 1) / total, height: 6, semanticLabel: "Review progress"),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl),
                  child: _ReviewQuestionBody(key: ValueKey(question.id), question: question),
                ),
              ),
              BottomActionBar(
                secondary: AppOutlineButton(
                  expand: false,
                  label: "Previous",
                  onPressed: _index > 0 ? () => setState(() => _index--) : null,
                ),
                primary: PrimaryButton(label: "Next", onPressed: _index < total - 1 ? () => setState(() => _index++) : null),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ReviewQuestionBody extends StatelessWidget {
  const _ReviewQuestionBody({super.key, required this.question});

  final ReviewQuestion question;

  @override
  Widget build(BuildContext context) {
    final isCorrect = question.isCorrect;
    final colors = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            StatusChip(
              label: isCorrect == null ? "Unanswered" : (isCorrect ? "Correct" : "Incorrect"),
              tone: isCorrect == null ? AppTone.neutral : (isCorrect ? AppTone.success : AppTone.danger),
              icon: isCorrect == null ? Icons.remove_rounded : (isCorrect ? AppIcons.check : Icons.close_rounded),
            ),
            TagChip(label: question.difficulty.label),
            if (question.topicName != null) TagChip(label: question.topicName!, tone: AppTone.purple),
          ],
        ),
        Gap.md,
        if (question.passageText != null) ...[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(color: colors.surfaceMuted, borderRadius: AppRadius.cardAll),
            child: Text(question.passageText!, style: context.text.bodyLarge?.copyWith(height: 1.55)),
          ),
          Gap.lg,
        ],
        Text(question.questionText, style: context.text.titleLarge?.copyWith(height: 1.4)),
        if (question.questionImageUrl != null) ...[
          Gap.md,
          ClipRRect(
            borderRadius: AppRadius.cardAll,
            child: Image.network(question.questionImageUrl!, semanticLabel: "Question image", errorBuilder: (_, __, ___) => const SizedBox.shrink()),
          ),
        ],
        Gap.lg,
        if (question.questionType.isNumericEntry)
          CareerCard(
            variant: CareerCardVariant.outlined,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
            child: Column(
              children: [
                FactRow(icon: AppIcons.profile, label: "Your answer", value: question.answerNumericValue?.toString() ?? "—"),
                FactRow(
                  icon: Icons.check_circle_outline_rounded,
                  label: "Correct answer",
                  value: question.correctNumericValue?.toString() ?? "—",
                  valueColor: AppTone.success.onTint(context),
                ),
              ],
            ),
          )
        else
          for (final option in question.options)
            _ReviewOptionTile(option: option, wasSelected: question.selectedOptionIds?.contains(option.id) ?? false),
        if (question.explanation != null) ...[
          Gap.md,
          CareerCard(
            color: colors.tint(colors.primary),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.lightbulb_outline_rounded, size: 18, color: colors.primary),
                    Gap.xs,
                    Text("Explanation", style: context.text.titleSmall),
                  ],
                ),
                Gap.xs,
                Text(question.explanation!, style: context.text.bodyLarge),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _ReviewOptionTile extends StatelessWidget {
  const _ReviewOptionTile({required this.option, required this.wasSelected});

  final TestOption option;
  final bool wasSelected;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final isCorrect = option.isCorrect ?? false;
    var border = colors.border;
    Color? fill;
    var icon = Icons.circle_outlined;
    var iconColor = colors.border;
    String? stateLabel;

    if (isCorrect) {
      border = AppColors.success;
      fill = AppTone.success.tint(context);
      icon = Icons.check_circle;
      iconColor = AppColors.success;
      stateLabel = "Correct option";
    } else if (wasSelected) {
      border = AppColors.error;
      fill = AppTone.danger.tint(context);
      icon = Icons.cancel;
      iconColor = AppColors.error;
      stateLabel = "Incorrect option";
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Semantics(
        label: [option.optionText ?? "", if (stateLabel != null) stateLabel, if (wasSelected) "your answer"].join(", "),
        excludeSemantics: true,
        child: Container(
          constraints: const BoxConstraints(minHeight: 56),
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
          decoration: BoxDecoration(border: Border.all(color: border, width: 1.4), borderRadius: AppRadius.cardAll, color: fill ?? colors.surface),
          child: Row(
            children: [
              Icon(icon, color: iconColor, size: 22),
              Gap.sm,
              Expanded(child: Text(option.optionText ?? "", style: context.text.bodyLarge)),
              if (wasSelected) ...[
                Gap.xs,
                Text("Your answer", style: context.text.labelSmall),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
