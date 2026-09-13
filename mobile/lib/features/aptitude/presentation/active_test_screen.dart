import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";
import "question_navigator_sheet.dart";
import "submit_confirmation_dialog.dart";

/// The exam screen (spec §17-19): header with section/progress/timer, the current question,
/// Previous/Next/Flag/Navigator/Submit controls. Deliberately carries no ad placement.
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
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(examState.error?.userMessage ?? "Unable to load this test.", textAlign: TextAlign.center),
          ),
        ),
      );
    }

    final session = examState.session!;
    final question = examState.currentQuestion;
    final total = session.questions.length;
    final index = examState.currentIndex;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final leave = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text("Leave this test?"),
            content: const Text("Your progress is saved. You can resume this test later from the Prepare tab."),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Stay")),
              TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Leave")),
            ],
          ),
        );
        if (leave == true && context.mounted) context.pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(question?.categoryName ?? "Test"),
          actions: [
            if (examState.hasUnsyncedChanges)
              const Padding(
                padding: EdgeInsets.only(right: 8),
                child: Tooltip(
                  message: "Some answers haven't synced yet — they'll upload once you're back online.",
                  child: Icon(Icons.cloud_off, color: AppColors.warning),
                ),
              ),
            if (session.expiresAt != null) _TimerBadge(remainingSeconds: examState.remainingSeconds),
            const SizedBox(width: 8),
            IconButton(
              icon: Icon(question?.isFlagged ?? false ? Icons.flag : Icons.flag_outlined,
                  color: (question?.isFlagged ?? false) ? AppColors.warning : null),
              onPressed: question == null ? null : () => controller.toggleFlag(question.id),
            ),
            IconButton(
              icon: const Icon(Icons.grid_view_rounded),
              onPressed: () => showQuestionNavigatorSheet(context, sessionId: widget.sessionId),
            ),
          ],
        ),
        body: Column(
          children: [
            LinearProgressIndicator(value: total == 0 ? 0 : (index + 1) / total),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text("Question ${index + 1} of $total", style: const TextStyle(color: AppColors.muted)),
                  if (question?.topicName != null)
                    Text(question!.topicName!, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
                ],
              ),
            ),
            Expanded(
              child: question == null
                  ? const Center(child: Text("No questions in this session."))
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
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
              onPrevious: controller.previous,
              onNext: controller.next,
              onSubmit: () => _confirmAndSubmit(context, controller, session),
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
    final isLow = seconds <= 60;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: (isLow ? AppColors.danger : AppColors.blue).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.timer_outlined, size: 16, color: isLow ? AppColors.danger : AppColors.blue),
          const SizedBox(width: 4),
          Text(
            "${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}",
            style: TextStyle(color: isLow ? AppColors.danger : AppColors.blue, fontWeight: FontWeight.w600),
          ),
        ],
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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
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
        if (question.questionType.isNumericEntry)
          TextField(
            controller: _numericController,
            enabled: !widget.readOnly,
            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
            decoration: const InputDecoration(labelText: "Your answer", border: OutlineInputBorder()),
            onChanged: (text) {
              final value = double.tryParse(text);
              if (value != null) widget.onNumericChanged(value);
            },
          )
        else
          for (final option in question.options)
            _OptionTile(
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
    required this.option,
    required this.isSelected,
    required this.isMultiSelect,
    required this.readOnly,
    required this.onTap,
  });

  final TestOption option;
  final bool isSelected;
  final bool isMultiSelect;
  final bool readOnly;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: readOnly ? null : onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            border: Border.all(color: isSelected ? AppColors.blue : AppColors.muted.withValues(alpha: 0.3)),
            borderRadius: BorderRadius.circular(12),
            color: isSelected ? AppColors.blue.withValues(alpha: 0.06) : null,
          ),
          child: Row(
            children: [
              Icon(
                isMultiSelect
                    ? (isSelected ? Icons.check_box : Icons.check_box_outline_blank)
                    : (isSelected ? Icons.radio_button_checked : Icons.radio_button_off),
                color: isSelected ? AppColors.blue : AppColors.muted,
                size: 20,
              ),
              const SizedBox(width: 12),
              if (option.optionImageUrl != null)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(option.optionImageUrl!, width: 48, height: 48, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink()),
                  ),
                ),
              Expanded(child: Text(option.optionText ?? "")),
            ],
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
    required this.onPrevious,
    required this.onNext,
    required this.onSubmit,
  });

  final bool canGoPrevious;
  final bool canGoNext;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(color: AppColors.card, border: Border(top: BorderSide(color: Color(0x1A000000)))),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton(onPressed: canGoPrevious ? onPrevious : null, child: const Text("Previous")),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(onPressed: canGoNext ? onNext : null, child: const Text("Next")),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton(
                onPressed: onSubmit,
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
                child: const Text("Submit"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
