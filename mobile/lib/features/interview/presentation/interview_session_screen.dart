import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/interview_models.dart";
import "interview_providers.dart";
import "recording_controller.dart";
import "recording_widgets.dart";

/// The interview practice/mock session screen (spec §12/§17-18): question, guidance, notes,
/// self-assessment, and — for Mock Interview — a self-paced per-question timer. Covers both
/// Question Practice mode and Mock Interview mode in one screen since they share almost all of
/// their UI; the differences (timer visibility, self-rating prompt) are conditional on `mode`.
/// Distraction-free: no ads, no bottom navigation.
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
        body: ErrorState(
          title: "We couldn't open this session",
          message: state.error?.userMessage ?? "Unable to load this session.",
        ),
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
        titleSpacing: 0,
        title: Text(question?.categoryName ?? "Interview Practice", maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (state.hasUnsyncedChanges)
            const Padding(
              padding: EdgeInsets.only(right: 4),
              child: Tooltip(message: "Not synced yet — will upload once you're back online.", child: Icon(AppIcons.offline, color: AppColors.warning)),
            ),
          if (isMock && state.remainingSeconds != null) _TimerBadge(seconds: state.remainingSeconds!),
          TextButton(
            onPressed: () => _confirmEnd(context, controller),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text("End"),
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xxs, AppSpacing.pageH, AppSpacing.sm),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Text("Question ${index + 1} of $total", style: context.text.titleSmall),
                    const Spacer(),
                    StatusChip(label: isMock ? "Mock Interview" : "Practice", tone: isMock ? AppTone.warning : AppTone.primary, dense: true),
                  ],
                ),
                Gap.xs,
                CareerProgressBar(
                  value: total == 0 ? 0 : (index + 1) / total,
                  height: 6,
                  tone: AppTone.warning,
                  semanticLabel: "Interview progress",
                  semanticValue: "Question ${index + 1} of $total",
                ),
              ],
            ),
          ),
          Expanded(
            child: question == null
                ? const EmptyState(icon: AppIcons.interview, title: "No questions in this session.", message: "Go back and start a new session.")
                : SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl),
                    child: _QuestionBody(
                      key: ValueKey(question.id),
                      question: question,
                      sessionId: widget.sessionId,
                      showGuidance: _showGuidance,
                      onToggleGuidance: () => setState(() => _showGuidance = !_showGuidance),
                      answerController: _answerController,
                      notesController: _notesController,
                      onAnswerChanged: (text) => controller.answer(question.id, answerText: text),
                      onNotesChanged: (text) => controller.answer(question.id, notes: text),
                      onRecordingReady: (path, duration) => controller.answer(question.id, audioPath: path, audioDurationSeconds: duration),
                      onMarkPracticed: () => controller.answer(question.id, isMarkedPracticed: true),
                      onToggleSaved: () => controller.answer(question.id, isSaved: !(question.answerState?.isSaved ?? false)),
                      onSelfAssess: (rating, usedStar, gaveMetric, exact) => controller.answer(
                        question.id,
                        selfRating: rating,
                        usedStar: usedStar,
                        gaveMeasurableResult: gaveMetric,
                        answeredExactQuestion: exact,
                      ),
                    ),
                  ),
          ),
          _BottomControls(
            canGoPrevious: index > 0,
            canGoNext: index < total - 1,
            onPrevious: controller.previous,
            onNext: controller.next,
            onSkip: question == null
                ? null
                : () {
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
    final tone = seconds <= 15 ? AppTone.danger : AppTone.primary;
    return Semantics(
      label: "Time remaining $minutes minutes $secs seconds",
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: tone.tint(context), borderRadius: AppRadius.pillAll),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.timer_outlined, size: 16, color: tone.onTint(context)),
            const SizedBox(width: 4),
            Text(
              "${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}",
              style: context.text.labelLarge?.copyWith(color: tone.onTint(context), fontFeatures: const [FontFeature.tabularFigures()]),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionBody extends StatelessWidget {
  const _QuestionBody({
    super.key,
    required this.question,
    required this.sessionId,
    required this.showGuidance,
    required this.onToggleGuidance,
    required this.answerController,
    required this.notesController,
    required this.onAnswerChanged,
    required this.onNotesChanged,
    required this.onRecordingReady,
    required this.onMarkPracticed,
    required this.onToggleSaved,
    required this.onSelfAssess,
  });

  final SessionQuestion question;
  final String sessionId;
  final bool showGuidance;
  final VoidCallback onToggleGuidance;
  final TextEditingController answerController;
  final TextEditingController notesController;
  final ValueChanged<String> onAnswerChanged;
  final ValueChanged<String> onNotesChanged;
  final void Function(String path, int durationSeconds) onRecordingReady;
  final VoidCallback onMarkPracticed;
  final VoidCallback onToggleSaved;
  final void Function(int rating, bool usedStar, bool gaveMetric, bool exact) onSelfAssess;

  @override
  Widget build(BuildContext context) {
    final isSaved = question.answerState?.isSaved ?? false;
    final isPracticed = question.answerState?.isMarkedPracticed ?? false;
    final colors = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CareerCard(
          variant: CareerCardVariant.feature,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: AppSpacing.xs,
                      children: [
                        TagChip(label: question.difficulty.label),
                        if (question.topicName != null) TagChip(label: question.topicName!, tone: AppTone.purple),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: isSaved ? "Remove from saved questions" : "Save question",
                    icon: Icon(isSaved ? AppIcons.savedSelected : AppIcons.saved, color: isSaved ? colors.primary : colors.textSecondary),
                    onPressed: onToggleSaved,
                  ),
                ],
              ),
              Gap.xs,
              Text(question.questionText, style: context.text.titleLarge?.copyWith(height: 1.4)),
              Gap.md,
              AppTextButton(
                label: showGuidance ? "Hide Guidance" : "Show Guidance",
                icon: showGuidance ? Icons.visibility_off_outlined : Icons.lightbulb_outline_rounded,
                onPressed: onToggleGuidance,
              ),
              if (showGuidance && question.answerGuidance != null) ...[
                Gap.xs,
                _GuidanceCard(guidance: question.answerGuidance!),
              ],
            ],
          ),
        ),
        Gap.xl,
        Text("Your Answer", style: context.text.titleMedium),
        const SizedBox(height: 2),
        Text("Record it, type it, or add notes — whatever works for you. You can combine all three.", style: context.text.bodySmall),
        Gap.sm,
        RecordingControls(
          target: RecordingTarget(sessionId: sessionId, questionId: question.id),
          onRecordingReady: onRecordingReady,
        ),
        Gap.sm,
        TextField(
          controller: answerController,
          minLines: 4,
          maxLines: 10,
          decoration: const InputDecoration(
            labelText: "Type your answer",
            hintText: "Optional — or just think it through and mark as practiced.",
            alignLabelWithHint: true,
          ),
          onChanged: onAnswerChanged,
        ),
        Gap.sm,
        TextField(
          controller: notesController,
          minLines: 1,
          maxLines: 3,
          decoration: const InputDecoration(labelText: "Notes", prefixIcon: Icon(Icons.sticky_note_2_outlined)),
          onChanged: onNotesChanged,
        ),
        if (question.answerState?.structureCheck != null) ...[
          Gap.sm,
          _StructureCheckCard(check: question.answerState!.structureCheck!),
        ],
        Gap.sm,
        isPracticed
            ? AppOutlineButton(label: "Mark as Practiced", icon: Icons.check_circle_rounded, onPressed: onMarkPracticed)
            : SecondaryButton(label: "Mark as Practiced", icon: Icons.check_circle_outline_rounded, onPressed: onMarkPracticed),
        Gap.xl,
        CareerCard(
          variant: CareerCardVariant.outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("How did that answer feel?", style: context.text.titleMedium),
              const SizedBox(height: 2),
              Text("Your own rating — it's never scored automatically.", style: context.text.bodySmall),
              Gap.sm,
              _SelfRatingRow(
                currentRating: question.answerState?.selfRating,
                onSelected: (rating) => onSelfAssess(
                  rating,
                  question.answerState?.usedStar ?? false,
                  question.answerState?.gaveMeasurableResult ?? false,
                  question.answerState?.answeredExactQuestion ?? false,
                ),
              ),
              Gap.xs,
              _SelfCheckToggle(
                label: "Did you use STAR?",
                value: question.answerState?.usedStar ?? false,
                onChanged: (v) => onSelfAssess(
                  question.answerState?.selfRating ?? 0,
                  v,
                  question.answerState?.gaveMeasurableResult ?? false,
                  question.answerState?.answeredExactQuestion ?? false,
                ),
              ),
              _SelfCheckToggle(
                label: "Did you give a measurable result?",
                value: question.answerState?.gaveMeasurableResult ?? false,
                onChanged: (v) => onSelfAssess(
                  question.answerState?.selfRating ?? 0,
                  question.answerState?.usedStar ?? false,
                  v,
                  question.answerState?.answeredExactQuestion ?? false,
                ),
              ),
              _SelfCheckToggle(
                label: "Did you answer the exact question?",
                value: question.answerState?.answeredExactQuestion ?? false,
                onChanged: (v) => onSelfAssess(
                  question.answerState?.selfRating ?? 0,
                  question.answerState?.usedStar ?? false,
                  question.answerState?.gaveMeasurableResult ?? false,
                  v,
                ),
              ),
            ],
          ),
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
    final colors = context.colors;
    Widget group(String title, List<String> items, {Color? color}) => Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: context.text.labelMedium?.copyWith(color: color)),
              const SizedBox(height: 2),
              BulletList(items: items),
            ],
          ),
        );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(color: colors.tint(colors.primary), borderRadius: AppRadius.mdAll),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (guidance.assessing?.isNotEmpty ?? false)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("What the interviewer is assessing", style: context.text.labelMedium),
                  const SizedBox(height: 2),
                  Text(guidance.assessing!, style: context.text.bodyLarge),
                ],
              ),
            ),
          if (guidance.strongAnswerIncludes.isNotEmpty) group("A strong answer includes", guidance.strongAnswerIncludes),
          if (guidance.commonMistakes.isNotEmpty) group("Common mistakes", guidance.commonMistakes, color: AppColors.error),
          if (guidance.technicalConcepts.isNotEmpty) group("Technical concepts to mention", guidance.technicalConcepts),
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
    final ok = check.flags.isEmpty;
    return CareerCard(
      variant: CareerCardVariant.muted,
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(ok ? Icons.check_circle_rounded : Icons.rule_rounded, size: 18, color: ok ? AppColors.success : AppColors.warning),
              Gap.xs,
              Expanded(child: Text("Answer Structure Check · ${check.wordCount} words", style: context.text.labelMedium)),
            ],
          ),
          Gap.xxs,
          if (ok)
            Text("Looks well-structured.", style: context.text.bodySmall?.copyWith(color: AppTone.success.onTint(context)))
          else
            for (final flag in check.flags) Text("• ${_flagLabel(flag)}", style: context.text.bodySmall),
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
    final colors = context.colors;
    return Row(
      children: [
        for (final rating in [1, 2, 3, 4, 5])
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Semantics(
                selected: currentRating == rating,
                label: "Rate $rating, ${_labels[rating]}",
                excludeSemantics: true,
                child: OutlinedButton(
                  onPressed: () => onSelected(rating),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 56),
                    backgroundColor: currentRating == rating ? colors.tint(colors.primary) : null,
                    side: BorderSide(color: currentRating == rating ? colors.primary : colors.border),
                    padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text("$rating", style: context.text.titleMedium?.copyWith(color: currentRating == rating ? colors.primary : null)),
                      FittedBox(child: Text(_labels[rating]!, style: context.text.labelSmall)),
                    ],
                  ),
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
      title: Text(label, style: context.text.bodyLarge),
      value: value,
      onChanged: onChanged,
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
    final colors = context.colors;
    return DecoratedBox(
      decoration: BoxDecoration(color: colors.surface, border: Border(top: BorderSide(color: colors.border))),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
          child: Row(
            children: [
              Expanded(child: OutlinedButton(onPressed: canGoPrevious ? onPrevious : null, child: const Text("Previous"))),
              Gap.xs,
              Expanded(child: OutlinedButton(onPressed: onSkip, child: const Text("Skip"))),
              Gap.xs,
              Expanded(
                child: canGoNext
                    ? ElevatedButton(onPressed: onNext, child: const Text("Next"))
                    : ElevatedButton(
                        onPressed: onEndInterview,
                        style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
                        child: const FittedBox(child: Text("End Interview")),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
