import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/interview_models.dart";
import "interview_providers.dart";

/// STAR story create/edit screen with a live, deterministic completeness check (spec §15) — no
/// AI grading, just concrete section-by-section presence/length checks recomputed on every save.
class StarStoryEditorScreen extends ConsumerStatefulWidget {
  const StarStoryEditorScreen({super.key, this.storyId});

  /// Null when creating a new story.
  final String? storyId;

  @override
  ConsumerState<StarStoryEditorScreen> createState() => _StarStoryEditorScreenState();
}

class _StarStoryEditorScreenState extends ConsumerState<StarStoryEditorScreen> {
  final _titleController = TextEditingController();
  final _situationController = TextEditingController();
  final _taskController = TextEditingController();
  final _actionController = TextEditingController();
  final _resultController = TextEditingController();
  final _lessonsController = TextEditingController();
  final _metricsController = TextEditingController();
  StarCategory _category = StarCategory.achievement;
  StarCompleteness? _completeness;
  bool _saving = false;
  bool _loadedExisting = false;

  @override
  void dispose() {
    for (final c in [_titleController, _situationController, _taskController, _actionController, _resultController, _lessonsController, _metricsController]) {
      c.dispose();
    }
    super.dispose();
  }

  void _loadFrom(StarStory story) {
    if (_loadedExisting) return;
    _loadedExisting = true;
    _titleController.text = story.title;
    _situationController.text = story.situation ?? "";
    _taskController.text = story.task ?? "";
    _actionController.text = story.action ?? "";
    _resultController.text = story.result ?? "";
    _lessonsController.text = story.lessons ?? "";
    _metricsController.text = story.metrics ?? "";
    _category = story.category;
    setState(() => _completeness = story.completeness);
  }

  Future<void> _save() async {
    if (_titleController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Give this story a title.")));
      return;
    }
    setState(() => _saving = true);
    try {
      final repo = ref.read(interviewRepositoryProvider);
      final StarStory saved;
      if (widget.storyId == null) {
        saved = await repo.createStarStory(
          title: _titleController.text.trim(),
          category: _category,
          situation: _situationController.text.trim(),
          task: _taskController.text.trim(),
          action: _actionController.text.trim(),
          result: _resultController.text.trim(),
          lessons: _lessonsController.text.trim(),
          metrics: _metricsController.text.trim(),
        );
      } else {
        saved = await repo.updateStarStory(
          widget.storyId!,
          title: _titleController.text.trim(),
          category: _category,
          situation: _situationController.text.trim(),
          task: _taskController.text.trim(),
          action: _actionController.text.trim(),
          result: _resultController.text.trim(),
          lessons: _lessonsController.text.trim(),
          metrics: _metricsController.text.trim(),
        );
      }
      setState(() => _completeness = saved.completeness);
      ref.invalidate(starStoriesProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Saved.")));
        context.pop();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _delete() async {
    if (widget.storyId == null) return;
    final confirmed = await showCareerDialog(
      context: context,
      title: "Delete this story?",
      message: "This STAR story will be removed permanently.",
      confirmLabel: "Delete",
      destructive: true,
    );
    if (!confirmed) return;
    await ref.read(interviewRepositoryProvider).deleteStarStory(widget.storyId!);
    ref.invalidate(starStoriesProvider);
    if (mounted) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.storyId != null) {
      final storyAsync = ref.watch(starStoryProvider(widget.storyId!));
      storyAsync.whenData(_loadFrom);
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.storyId == null ? "New STAR Story" : "Edit STAR Story"),
        actions: [
          if (widget.storyId != null) IconButton(tooltip: "Delete story", icon: const Icon(AppIcons.delete), onPressed: _delete),
        ],
      ),
      bottomNavigationBar: BottomActionBar(primary: PrimaryButton(label: "Save", isLoading: _saving, onPressed: _save)),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          TextField(
            controller: _titleController,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: "Title", hintText: "e.g. Restoring a failed pump overnight"),
          ),
          Gap.md,
          DropdownButtonFormField<StarCategory>(
            initialValue: _category,
            decoration: const InputDecoration(labelText: "Category"),
            items: [for (final c in StarCategory.values) DropdownMenuItem(value: c, child: Text(c.label))],
            onChanged: (v) => setState(() => _category = v ?? _category),
          ),
          if (_completeness != null) ...[
            Gap.lg,
            _CompletenessCard(completeness: _completeness!),
          ],
          Gap.xl,
          _StarField(
            letter: "S",
            label: "Situation",
            prompt: "Where were you, and what was happening?",
            controller: _situationController,
            status: _completeness?.sections["situation"],
          ),
          _StarField(
            letter: "T",
            label: "Task",
            prompt: "What were you responsible for?",
            controller: _taskController,
            status: _completeness?.sections["task"],
          ),
          _StarField(
            letter: "A",
            label: "Action",
            prompt: "What did you do? Use \"I\" statements.",
            controller: _actionController,
            status: _completeness?.sections["action"],
          ),
          _StarField(
            letter: "R",
            label: "Result",
            prompt: "What changed because of your actions?",
            controller: _resultController,
            status: _completeness?.sections["result"],
          ),
          CareerCard(
            variant: CareerCardVariant.outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Strengthen your story", style: context.text.titleSmall),
                const SizedBox(height: 2),
                Text("Optional details interviewers remember.", style: context.text.bodySmall),
                Gap.sm,
                TextField(
                  controller: _metricsController,
                  decoration: const InputDecoration(labelText: "Metrics (optional)", prefixIcon: Icon(Icons.trending_up_rounded)),
                ),
                Gap.sm,
                TextField(
                  controller: _lessonsController,
                  minLines: 1,
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: "Lessons learned (optional)", prefixIcon: Icon(Icons.school_outlined)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _statusLabel(String status) => switch (status) {
      "missing" => "Missing",
      "brief" => "Brief",
      "complete" => "Complete",
      "strong" => "Strong",
      _ => status,
    };

AppTone _statusTone(String status) => switch (status) {
      "missing" => AppTone.danger,
      "brief" => AppTone.warning,
      "strong" => AppTone.success,
      _ => AppTone.primary,
    };

class _StarField extends StatelessWidget {
  const _StarField({required this.letter, required this.label, required this.prompt, required this.controller, this.status});

  final String letter;
  final String label;
  final String prompt;
  final TextEditingController controller;
  final String? status;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              ExcludeSemantics(
                child: Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(color: colors.primary, borderRadius: AppRadius.smAll),
                  alignment: Alignment.center,
                  child: Text(letter, style: context.text.labelLarge?.copyWith(color: Colors.white)),
                ),
              ),
              Gap.xs,
              Expanded(child: Text(prompt, style: context.text.bodySmall)),
              if (status != null) StatusChip(label: _statusLabel(status!), tone: _statusTone(status!), dense: true),
            ],
          ),
          Gap.xs,
          TextField(
            controller: controller,
            minLines: 3,
            maxLines: 8,
            textCapitalization: TextCapitalization.sentences,
            decoration: InputDecoration(labelText: label, alignLabelWithHint: true),
          ),
        ],
      ),
    );
  }
}

class _CompletenessCard extends StatelessWidget {
  const _CompletenessCard({required this.completeness});

  final StarCompleteness completeness;

  static const _sectionKeys = ["situation", "task", "action", "result"];

  @override
  Widget build(BuildContext context) {
    final strongOrComplete = _sectionKeys.where((k) => const {"complete", "strong"}.contains(completeness.sections[k])).length;
    return CareerCard(
      variant: CareerCardVariant.outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text("STAR Completeness", style: context.text.titleSmall)),
              StatusChip(
                label: completeness.isComplete ? "Ready to use" : "$strongOrComplete of 4 sections complete",
                tone: completeness.isComplete ? AppTone.success : AppTone.warning,
                dense: true,
              ),
            ],
          ),
          Gap.sm,
          Row(
            children: [
              for (final (i, key) in _sectionKeys.indexed) ...[
                if (i > 0) Gap.xxs,
                Expanded(
                  child: Semantics(
                    label: "${key[0].toUpperCase()}${key.substring(1)}: ${_statusLabel(completeness.sections[key] ?? "missing")}",
                    excludeSemantics: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          height: 6,
                          decoration: BoxDecoration(
                            color: _statusTone(completeness.sections[key] ?? "missing").color(context),
                            borderRadius: AppRadius.pillAll,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "${key[0].toUpperCase()} · ${_statusLabel(completeness.sections[key] ?? "missing")}",
                          style: context.text.labelSmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (completeness.gaps.isNotEmpty) ...[
            Gap.sm,
            for (final gap in completeness.gaps)
              Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.arrow_right_rounded, size: 18, color: AppColors.warning),
                    Expanded(child: Text(_gapLabel(gap), style: context.text.bodySmall)),
                  ],
                ),
              ),
          ],
          Gap.xs,
          Text("Checked by simple structure rules — not AI scoring.", style: context.text.labelSmall),
        ],
      ),
    );
  }

  String _gapLabel(String gap) => switch (gap) {
        "no_situation" => "Situation is missing",
        "no_task" => "Task is missing",
        "no_action" => "Action is missing",
        "very_short_action" => "Action is very short",
        "no_clear_personal_contribution" => "No clear personal contribution in Action — use \"I\" statements",
        "no_result" => "Result is missing",
        "missing_measurable_outcome" => "Result is missing a measurable outcome",
        _ => gap,
      };
}
