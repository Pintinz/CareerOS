import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";
import "question_navigator_sheet.dart";
import "submit_confirmation_dialog.dart";

/// The exam screen (spec §17-19): distraction-free — section, "Question X of Y", timer, progress,
/// the question and its answers, then Previous/Next/Submit. Deliberately carries no ad placement
/// and no bottom navigation.
class ActiveTestScreen extends ConsumerStatefulWidget {
  const ActiveTestScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  ConsumerState<ActiveTestScreen> createState() => _ActiveTestScreenState();
}

class _ActiveTestScreenState extends ConsumerState<ActiveTestScreen> {
  bool _navigatedToResults = false;

  @override
  Widget build(BuildContext context) {
    final examState = ref.watch(examControllerProvider(widget.sessionId));
    final controller = ref.read(examControllerProvider(widget.sessionId).notifier);

    ref.listen(examControllerProvider(widget.sessionId), (previous, next) {
      if (!_navigatedToResults && next.isSubmitted && (previous == null || !previous.isSubmitted)) {
        _navigatedToResults = true;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) context.pushReplacement("/prepare/aptitude/sessions/${widget.sessionId}/results");
        });
      }
    });

    if (examState.isLoading && examState.session == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (examState.session == null) {
      return Scaffold(
        appBar: AppBar(title: const Text("Test")),
        body: ErrorState(
          title: "We couldn't open this test",
          message: examState.error?.userMessage ?? "Unable to load this test.",
        ),
      );
    }

    final session = examState.session!;
    final question = examState.currentQuestion;
    final total = session.questions.length;
    final index = examState.currentIndex;
    final colors = context.colors;
    final isFlagged = question?.isFlagged ?? false;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final leave = await showCareerDialog(
          context: context,
          title: "Leave this test?",
          message: "Your progress is saved. You can resume this test later from the Prepare tab.",
          confirmLabel: "Leave",
          cancelLabel: "Stay",
        );
        if (leave && context.mounted) context.pop();
      },
      child: Scaffold(
        appBar: AppBar(
          titleSpacing: 0,
          title: Text(question?.categoryName ?? "Test", maxLines: 1, overflow: TextOverflow.ellipsis),
          actions: [
            if (examState.hasUnsyncedChanges)
              const Padding(
                padding: EdgeInsets.only(right: 4),
                child: Tooltip(
                  message: "Some answers haven't synced yet — they'll upload once you're back online.",
                  child: Icon(AppIcons.offline, color: AppColors.warning),
                ),
              ),
            if (session.expiresAt != null) _TimerBadge(remainingSeconds: examState.remainingSeconds),
            IconButton(
              tooltip: isFlagged ? "Remove flag" : "Flag for review",
              icon: Icon(isFlagged ? Icons.flag : Icons.flag_outlined, color: isFlagged ? AppColors.warning : null),
              onPressed: question == null ? null : () => controller.toggleFlag(question.id),
            ),
            IconButton(
              tooltip: "Question navigator",
              icon: const Icon(Icons.grid_view_rounded),
              onPressed: () => showQuestionNavigatorSheet(context, sessionId: widget.sessionId),
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
                      if (question?.topicName != null)
                        Flexible(child: StatusChip(label: question!.topicName!, tone: AppTone.primary, dense: true)),
                    ],
                  ),
                  Gap.xs,
                  CareerProgressBar(
                    value: total == 0 ? 0 : (index + 1) / total,
                    height: 6,
                    semanticLabel: "Test progress",
                    semanticValue: "Question ${index + 1} of $total",
                  ),
                ],
              ),
            ),
            Expanded(
              child: question == null
                  ? const EmptyState(icon: AppIcons.aptitude, title: "No questions in this session.", message: "Go back and start a new test.")
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl),
                      child: _QuestionBody(
                        key: ValueKey(question.id),
                        question: question,
                        readOnly: examState.isSubmitted,
                        onOptionsChanged: (ids) => controller.answerOptions(question.id, ids),
                        onNumericChanged: (value) => controller.answerNumeric(question.id, value),
                      ),
                    ),
            ),
            _BottomControls(
              canGoPrevious: index > 0,
              canGoNext: index < total - 1,
              isLast: index >= total - 1,
              onPrevious: controller.previous,
              onNext: controller.next,
              onSubmit: () => _confirmAndSubmit(context, controller, session),
              background: colors.surface,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmAndSubmit(BuildContext context, ExamController controller, TestSessionDetail session) async {
    final answered = session.questions.where((q) => q.isAnswered).length;
    final flagged = session.questions.where((q) => q.isFlagged).length;
    final confirmed = await showSubmitConfirmationDialog(
      context,
      answered: answered,
      unanswered: session.questions.length - answered,
      flagged: flagged,
      remainingSeconds: ref.read(examControllerProvider(widget.sessionId)).remainingSeconds,
    );
    if (confirmed == true) {
      await controller.submit();
    }
  }
}

class _TimerBadge extends StatelessWidget {
  const _TimerBadge({required this.remainingSeconds});

  final int? remainingSeconds;

  @override
  Widget build(BuildContext context) {
    final seconds = remainingSeconds;
    if (seconds == null) return const SizedBox.shrink();
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    final tone = seconds <= 60 ? AppTone.danger : (seconds <= 300 ? AppTone.warning : AppTone.primary);
    final label = "${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}";
    return Semantics(
      label: "Time remaining $minutes minutes $secs seconds",
      excludeSemantics: true,
      child: Container(
        margin: const EdgeInsets.only(right: AppSpacing.xxs),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: tone.tint(context), borderRadius: AppRadius.pillAll),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.timer_outlined, size: 16, color: tone.onTint(context)),
            const SizedBox(width: 4),
            Text(
              label,
              style: context.text.labelLarge?.copyWith(
                color: tone.onTint(context),
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionBody extends StatefulWidget {
  const _QuestionBody({
    super.key,
    required this.question,
    required this.readOnly,
    required this.onOptionsChanged,
    required this.onNumericChanged,
  });

  final SessionQuestion question;
  final bool readOnly;
  final ValueChanged<List<String>> onOptionsChanged;
  final ValueChanged<double> onNumericChanged;

  @override
  State<_QuestionBody> createState() => _QuestionBodyState();
}

class _QuestionBodyState extends State<_QuestionBody> {
  late final TextEditingController _numericController;

  @override
  void initState() {
    super.initState();
    _numericController = TextEditingController(
      text: widget.question.answerState?.answerNumericValue?.toString() ?? "",
    );
  }

  @override
  void dispose() {
    _numericController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final question = widget.question;
    final selected = question.answerState?.selectedOptionIds ?? const [];
    final colors = context.colors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
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
            child: Image.network(
              question.questionImageUrl!,
              semanticLabel: "Question image",
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        ],
        Gap.lg,
        if (question.questionType.isMultiSelect) ...[
          Text("Select all that apply", style: context.text.labelMedium),
          Gap.xs,
        ],
        if (question.questionType.isNumericEntry)
          TextField(
            controller: _numericController,
            enabled: !widget.readOnly,
            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
            style: context.text.titleLarge,
            decoration: const InputDecoration(labelText: "Your answer"),
            onChanged: (text) {
              final value = double.tryParse(text);
              if (value != null) widget.onNumericChanged(value);
            },
          )
        else
          for (final (i, option) in question.options.indexed)
            _OptionTile(
              letter: String.fromCharCode(65 + i),
              option: option,
              isSelected: selected.contains(option.id),
              isMultiSelect: question.questionType.isMultiSelect,
              readOnly: widget.readOnly,
              onTap: () {
                if (question.questionType.isMultiSelect) {
                  final next = List<String>.from(selected);
                  if (next.contains(option.id)) {
                    next.remove(option.id);
                  } else {
                    next.add(option.id);
                  }
                  widget.onOptionsChanged(next);
                } else {
                  widget.onOptionsChanged([option.id]);
                }
              },
            ),
      ],
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.letter,
    required this.option,
    required this.isSelected,
    required this.isMultiSelect,
    required this.readOnly,
    required this.onTap,
  });

  final String letter;
  final TestOption option;
  final bool isSelected;
  final bool isMultiSelect;
  final bool readOnly;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Semantics(
        selected: isSelected,
        button: true,
        label: "Option $letter",
        child: Material(
          color: isSelected ? colors.tint(colors.primary) : colors.surface,
          shape: RoundedRectangleBorder(
            borderRadius: AppRadius.cardAll,
            side: BorderSide(color: isSelected ? colors.primary : colors.border, width: isSelected ? 1.6 : 1),
          ),
          child: InkWell(
            borderRadius: AppRadius.cardAll,
            onTap: readOnly ? null : onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 56),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                child: Row(
                  children: [
                    AnimatedContainer(
                      duration: AppMotion.of(context, AppMotion.fast),
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        color: isSelected ? colors.primary : colors.surfaceMuted,
                        borderRadius: BorderRadius.circular(isMultiSelect ? 8 : 15),
                      ),
                      alignment: Alignment.center,
                      child: Text(letter, style: context.text.labelLarge?.copyWith(color: isSelected ? Colors.white : colors.textSecondary)),
                    ),
                    Gap.sm,
                    if (option.optionImageUrl != null)
                      Padding(
                        padding: const EdgeInsets.only(right: AppSpacing.xs),
                        child: ClipRRect(
                          borderRadius: AppRadius.smAll,
                          child: Image.network(
                            option.optionImageUrl!,
                            width: 56,
                            height: 56,
                            fit: BoxFit.cover,
                            semanticLabel: "Option $letter image",
                            errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                          ),
                        ),
                      ),
                    Expanded(child: Text(option.optionText ?? "", style: context.text.bodyLarge)),
                    Gap.xs,
                    Icon(
                      isMultiSelect
                          ? (isSelected ? Icons.check_box : Icons.check_box_outline_blank)
                          : (isSelected ? Icons.radio_button_checked : Icons.radio_button_off),
                      color: isSelected ? colors.primary : colors.border,
                      size: 22,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BottomControls extends StatelessWidget {
  const _BottomControls({
    required this.canGoPrevious,
    required this.canGoNext,
    required this.isLast,
    required this.onPrevious,
    required this.onNext,
    required this.onSubmit,
    required this.background,
  });

  final bool canGoPrevious;
  final bool canGoNext;
  final bool isLast;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final VoidCallback onSubmit;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(color: background, border: Border(top: BorderSide(color: context.colors.border))),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
          child: Row(
            children: [
              Expanded(child: OutlinedButton(onPressed: canGoPrevious ? onPrevious : null, child: const Text("Previous"))),
              Gap.xs,
              Expanded(child: OutlinedButton(onPressed: canGoNext ? onNext : null, child: const Text("Next"))),
              Gap.xs,
              Expanded(
                child: ElevatedButton(
                  onPressed: onSubmit,
                  style: isLast ? null : ElevatedButton.styleFrom(backgroundColor: AppColors.success),
                  child: const Text("Submit"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
