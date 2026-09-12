import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../data/interview_models.dart";
import "interview_providers.dart";

/// The interview practice/mock session screen (spec §12/§17-18): question, guidance, notes,
/// self-assessment, and — for Mock Interview — a self-paced per-question timer. Covers both
/// Question Practice mode and Mock Interview mode in one screen since they share almost all of
/// their UI; the differences (timer visibility, self-rating prompt) are conditional on `mode`.
class InterviewSessionScreen extends ConsumerStatefulWidget {
  const InterviewSessionScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  ConsumerState<InterviewSessionScreen> createState() => _InterviewSessionScreenState();
}

class _InterviewSessionScreenState extends ConsumerState<InterviewSessionScreen> {
  bool _navigatedToResults = false;
  bool _showGuidance = false;
  final TextEditingController _answerController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();
  String? _loadedQuestionId;

  @override
  void dispose() {
    _answerController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _syncControllers(SessionQuestion? question) {
    if (question == null || question.id == _loadedQuestionId) return;
    _loadedQuestionId = question.id;
    _answerController.text = question.answerState?.answerText ?? "";
    _notesController.text = question.answerState?.notes ?? "";
    _showGuidance = false;
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(interviewSessionControllerProvider(widget.sessionId));
    final controller = ref.read(interviewSessionControllerProvider(widget.sessionId).notifier);

    ref.listen(interviewSessionControllerProvider(widget.sessionId), (previous, next) {
      if (!_navigatedToResults && next.isCompleted && (previous == null || !previous.isCompleted)) {
        _navigatedToResults = true;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) context.pushReplacement("/prepare/interview/sessions/${widget.sessionId}/results");
        });
      }
    });

    if (state.isLoading && state.session == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (state.session == null) {
      return Scaffold(
        appBar: AppBar(title: const Text("Interview Practice")),
        body: Center(child: Text(state.error?.userMessage ?? "Unable to load this session.")),
      );
    }

    final session = state.session!;
    final question = state.currentQuestion;
    _syncControllers(question);
    final total = session.questions.length;
    final index = state.currentIndex;
    final isMock = session.mode == InterviewSessionMode.mock;

    return Scaffold(
      appBar: AppBar(
        title: Text(question?.categoryName ?? "Interview Practice"),
        actions: [
          if (state.hasUnsyncedChanges)
            const Padding(
              padding: EdgeInsets.only(right: 8),
              child: Tooltip(message: "Not synced yet — will upload once you're back online.", child: Icon(Icons.cloud_off, color: AppColors.warning)),
            ),
          if (isMock && state.remainingSeconds != null) _TimerBadge(seconds: state.remainingSeconds!),
          const SizedBox(width: 12),
          TextButton(
            onPressed: () => _confirmEnd(context, controller),
            child: const Text("End", style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
      body: Column(
        children: [
          LinearProgressIndicator(value: total == 0 ? 0 : (index + 1) / total),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Text("Question ${index + 1} of $total", style: const TextStyle(color: AppColors.muted)),
          ),
          Expanded(
            child: question == null
                ? const Center(child: Text("No questions in this session."))
                : SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                    child: _QuestionBody(
                      key: ValueKey(question.id),
                      question: question,
                      showGuidance: _showGuidance,
                      onToggleGuidance: () => setState(() => _showGuidance = !_showGuidance),
                      answerController: _answerController,
                      notesController: _notesController,
                      isMock: isMock,
                      onAnswerChanged: (text) => controller.answer(question.id, answerText: text),
                      onNotesChanged: (text) => controller.answer(question.id, notes: text),
                      onMarkPracticed: () => controller.answer(question.id, isMarkedPracticed: true),
                      onToggleSaved: () => controller.answer(question.id, isSaved: !(question.answerState?.isSaved ?? false)),
                      onSelfAssess: (rating, usedStar, gaveMetric, exact) => controller.answer(
                        question.id, selfRating: rating, usedStar: usedStar, gaveMeasurableResult: gaveMetric, answeredExactQuestion: exact,
                      ),
                    ),
                  ),
          ),
          _BottomControls(
            canGoPrevious: index > 0,
            canGoNext: index < total - 1,
            onPrevious: controller.previous,
            onNext: controller.next,
            onSkip: question == null ? null : () {
              controller.answer(question.id, isSkipped: true);
              if (index < total - 1) controller.next();
            },
            onEndInterview: () => _confirmEnd(context, controller),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmEnd(BuildContext context, InterviewSessionController controller) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("End this interview?"),
        content: const Text("Your progress is saved. This will mark the session complete and show your results."),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Keep Going")),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("End Interview")),
        ],
      ),
    );
    if (confirmed == true) await controller.complete();
  }
}

class _TimerBadge extends StatelessWidget {
  const _TimerBadge({required this.seconds});

  final int seconds;

  @override
  Widget build(BuildContext context) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    final isLow = seconds <= 15;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: (isLow ? AppColors.danger : AppColors.blue).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.timer_outlined, size: 16, color: isLow ? AppColors.danger : AppColors.blue),
          const SizedBox(width: 4),
          Text("${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}", style: TextStyle(color: isLow ? AppColors.danger : AppColors.blue, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _QuestionBody extends StatelessWidget {
  const _QuestionBody({
    super.key,
    required this.question,
    required this.showGuidance,
    required this.onToggleGuidance,
    required this.answerController,
    required this.notesController,
    required this.isMock,
    required this.onAnswerChanged,
    required this.onNotesChanged,
    required this.onMarkPracticed,
    required this.onToggleSaved,
    required this.onSelfAssess,
  });

  final SessionQuestion question;
  final bool showGuidance;
  final VoidCallback onToggleGuidance;
  final TextEditingController answerController;
  final TextEditingController notesController;
  final bool isMock;
  final ValueChanged<String> onAnswerChanged;
  final ValueChanged<String> onNotesChanged;
  final VoidCallback onMarkPracticed;
  final VoidCallback onToggleSaved;
  final void Function(int rating, bool usedStar, bool gaveMetric, bool exact) onSelfAssess;

  @override
  Widget build(BuildContext context) {
    final isSaved = question.answerState?.isSaved ?? false;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Wrap(spacing: 8, children: [
          _Badge(label: question.difficulty.label, color: AppColors.blue),
          if (question.topicName != null) _Badge(label: question.topicName!, color: AppColors.purple),
        ]),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: Text(question.questionText, style: Theme.of(context).textTheme.titleLarge)),
            IconButton(
              icon: Icon(isSaved ? Icons.bookmark : Icons.bookmark_border, color: isSaved ? AppColors.blue : AppColors.muted),
              onPressed: onToggleSaved,
            ),
          ],
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: onToggleGuidance,
          icon: Icon(showGuidance ? Icons.visibility_off_outlined : Icons.lightbulb_outline),
          label: Text(showGuidance ? "Hide Guidance" : "Show Guidance"),
        ),
        if (showGuidance && question.answerGuidance != null) ...[
          const SizedBox(height: 12),
          _GuidanceCard(guidance: question.answerGuidance!),
        ],
        const SizedBox(height: 20),
        Text("Your Answer", style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: answerController,
          maxLines: 6,
          decoration: const InputDecoration(hintText: "Type your answer (optional) — or just think it through and mark as practiced.", border: OutlineInputBorder()),
          onChanged: onAnswerChanged,
        ),
        const SizedBox(height: 12),
        TextField(
          controller: notesController,
          maxLines: 2,
          decoration: const InputDecoration(hintText: "Add notes", border: OutlineInputBorder()),
          onChanged: onNotesChanged,
        ),
        const SizedBox(height: 12),
        if (question.answerState?.structureCheck != null) _StructureCheckCard(check: question.answerState!.structureCheck!),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: onMarkPracticed,
          icon: const Icon(Icons.check_circle_outline),
          label: const Text("Mark as Practiced"),
        ),
        const SizedBox(height: 20),
        Text("How did that answer feel?", style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _SelfRatingRow(currentRating: question.answerState?.selfRating, onSelected: (rating) {
          onSelfAssess(
            rating,
            question.answerState?.usedStar ?? false,
            question.answerState?.gaveMeasurableResult ?? false,
            question.answerState?.answeredExactQuestion ?? false,
          );
        }),
        const SizedBox(height: 8),
        _SelfCheckToggle(
          label: "Did you use STAR?",
          value: question.answerState?.usedStar ?? false,
          onChanged: (v) => onSelfAssess(question.answerState?.selfRating ?? 0, v, question.answerState?.gaveMeasurableResult ?? false, question.answerState?.answeredExactQuestion ?? false),
        ),
        _SelfCheckToggle(
          label: "Did you give a measurable result?",
          value: question.answerState?.gaveMeasurableResult ?? false,
          onChanged: (v) => onSelfAssess(question.answerState?.selfRating ?? 0, question.answerState?.usedStar ?? false, v, question.answerState?.answeredExactQuestion ?? false),
        ),
        _SelfCheckToggle(
          label: "Did you answer the exact question?",
          value: question.answerState?.answeredExactQuestion ?? false,
          onChanged: (v) => onSelfAssess(question.answerState?.selfRating ?? 0, question.answerState?.usedStar ?? false, question.answerState?.gaveMeasurableResult ?? false, v),
        ),
      ],
    );
  }
}

class _GuidanceCard extends StatelessWidget {
  const _GuidanceCard({required this.guidance});

  final AnswerGuidance guidance;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (guidance.assessing?.isNotEmpty ?? false) ...[
            const Text("What the interviewer is assessing", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
            const SizedBox(height: 2),
            Text(guidance.assessing!),
            const SizedBox(height: 10),
          ],
          if (guidance.strongAnswerIncludes.isNotEmpty) ...[
            const Text("A strong answer includes", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
            for (final item in guidance.strongAnswerIncludes) Text("• $item"),
            const SizedBox(height: 10),
          ],
          if (guidance.commonMistakes.isNotEmpty) ...[
            const Text("Common mistakes", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: AppColors.danger)),
            for (final item in guidance.commonMistakes) Text("• $item"),
            const SizedBox(height: 10),
          ],
          if (guidance.technicalConcepts.isNotEmpty) ...[
            const Text("Technical concepts to mention", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
            for (final item in guidance.technicalConcepts) Text("• $item"),
          ],
        ],
      ),
    );
  }
}

class _StructureCheckCard extends StatelessWidget {
  const _StructureCheckCard({required this.check});

  final AnswerStructureCheck check;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(10)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Answer Structure Check · ${check.wordCount} words", style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
          if (check.flags.isEmpty)
            const Text("Looks well-structured.", style: TextStyle(fontSize: 12, color: AppColors.success))
          else
            for (final flag in check.flags) Text("• ${_flagLabel(flag)}", style: const TextStyle(fontSize: 12, color: AppColors.muted)),
        ],
      ),
    );
  }

  String _flagLabel(String flag) => switch (flag) {
        "very_short_answer" => "This answer is quite short.",
        "below_recommended_length" => "Consider adding a bit more detail.",
        "excessive_length" => "This answer is quite long — consider tightening it.",
        "no_measurable_result_detected" => "No number or metric detected — consider quantifying the result.",
        "no_star_structure_detected" => "No clear Situation/Task/Action/Result structure detected.",
        _ => flag,
      };
}

class _SelfRatingRow extends StatelessWidget {
  const _SelfRatingRow({required this.currentRating, required this.onSelected});

  final int? currentRating;
  final ValueChanged<int> onSelected;

  static const _labels = {1: "Poor", 2: "Weak", 3: "Fair", 4: "Strong", 5: "Excellent"};

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (final rating in [1, 2, 3, 4, 5])
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: OutlinedButton(
                onPressed: () => onSelected(rating),
                style: OutlinedButton.styleFrom(
                  backgroundColor: currentRating == rating ? AppColors.blue.withValues(alpha: 0.1) : null,
                  side: BorderSide(color: currentRating == rating ? AppColors.blue : AppColors.muted.withValues(alpha: 0.3)),
                  padding: const EdgeInsets.symmetric(vertical: 10),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text("$rating", style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(_labels[rating]!, style: const TextStyle(fontSize: 10)),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _SelfCheckToggle extends StatelessWidget {
  const _SelfCheckToggle({required this.label, required this.value, required this.onChanged});

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(label, style: const TextStyle(fontSize: 14)),
      value: value,
      onChanged: onChanged,
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

class _BottomControls extends StatelessWidget {
  const _BottomControls({
    required this.canGoPrevious,
    required this.canGoNext,
    required this.onPrevious,
    required this.onNext,
    required this.onSkip,
    required this.onEndInterview,
  });

  final bool canGoPrevious;
  final bool canGoNext;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final VoidCallback? onSkip;
  final VoidCallback onEndInterview;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(color: AppColors.card, border: Border(top: BorderSide(color: Color(0x1A000000)))),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(child: OutlinedButton(onPressed: canGoPrevious ? onPrevious : null, child: const Text("Previous"))),
            const SizedBox(width: 8),
            Expanded(child: OutlinedButton(onPressed: onSkip, child: const Text("Skip"))),
            const SizedBox(width: 8),
            Expanded(
              child: canGoNext
                  ? ElevatedButton(onPressed: onNext, child: const Text("Next"))
                  : ElevatedButton(
                      onPressed: onEndInterview,
                      style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
                      child: const Text("End Interview"),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
