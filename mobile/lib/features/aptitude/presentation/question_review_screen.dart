import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
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
        error: (e, _) => Center(child: Text(e.userMessage)),
        data: (review) {
          if (review.questions.isEmpty) {
            return const Center(child: Text("No questions to review.", style: TextStyle(color: AppColors.muted)));
          }
          final question = review.questions[_index.clamp(0, review.questions.length - 1)];
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                child: Text("Question ${_index + 1} of ${review.questions.length}", style: const TextStyle(color: AppColors.muted)),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: _ReviewQuestionBody(question: question),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(color: AppColors.card, border: Border(top: BorderSide(color: Color(0x1A000000)))),
                child: SafeArea(
                  top: false,
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _index > 0 ? () => setState(() => _index--) : null,
                          child: const Text("Previous"),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: _index < review.questions.length - 1 ? () => setState(() => _index++) : null,
                          child: const Text("Next"),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ReviewQuestionBody extends StatelessWidget {
  const _ReviewQuestionBody({required this.question});

  final ReviewQuestion question;

  @override
  Widget build(BuildContext context) {
    final isCorrect = question.isCorrect;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            _Badge(
              label: isCorrect == null ? "Unanswered" : (isCorrect ? "Correct" : "Incorrect"),
              color: isCorrect == null ? AppColors.muted : (isCorrect ? AppColors.success : AppColors.danger),
            ),
            _Badge(label: question.difficulty.label, color: AppColors.blue),
            if (question.topicName != null) _Badge(label: question.topicName!, color: AppColors.purple),
          ],
        ),
        const SizedBox(height: 16),
        if (question.passageText != null) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12)),
            child: Text(question.passageText!, style: const TextStyle(height: 1.4)),
          ),
          const SizedBox(height: 16),
        ],
        Text(question.questionText, style: Theme.of(context).textTheme.titleLarge),
        if (question.questionImageUrl != null) ...[
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(question.questionImageUrl!, errorBuilder: (_, __, ___) => const SizedBox.shrink()),
          ),
        ],
        const SizedBox(height: 20),
        if (question.questionType.isNumericEntry) ...[
          _AnswerRow(label: "Your answer", value: question.answerNumericValue?.toString() ?? "—"),
          _AnswerRow(label: "Correct answer", value: question.correctNumericValue?.toString() ?? "—"),
        ] else
          for (final option in question.options)
            _ReviewOptionTile(
              option: option,
              wasSelected: question.selectedOptionIds?.contains(option.id) ?? false,
            ),
        if (question.explanation != null) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(12)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Explanation", style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Text(question.explanation!),
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
    final isCorrect = option.isCorrect ?? false;
    Color borderColor = AppColors.muted.withValues(alpha: 0.3);
    IconData icon = Icons.circle_outlined;
    Color iconColor = AppColors.muted;

    if (isCorrect) {
      borderColor = AppColors.success;
      icon = Icons.check_circle;
      iconColor = AppColors.success;
    } else if (wasSelected) {
      borderColor = AppColors.danger;
      icon = Icons.cancel;
      iconColor = AppColors.danger;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(color: borderColor),
          borderRadius: BorderRadius.circular(12),
          color: isCorrect ? AppColors.success.withValues(alpha: 0.06) : null,
        ),
        child: Row(
          children: [
            Icon(icon, color: iconColor, size: 20),
            const SizedBox(width: 12),
            Expanded(child: Text(option.optionText ?? "")),
            if (wasSelected) const Text("Your answer", style: TextStyle(fontSize: 11, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }
}

class _AnswerRow extends StatelessWidget {
  const _AnswerRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(width: 140, child: Text(label, style: const TextStyle(color: AppColors.muted))),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
      child: Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
