import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
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
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Delete this story?"),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Cancel")),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Delete", style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
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
          if (widget.storyId != null) IconButton(icon: const Icon(Icons.delete_outline), onPressed: _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(controller: _titleController, decoration: const InputDecoration(labelText: "Title", border: OutlineInputBorder())),
          const SizedBox(height: 16),
          DropdownButtonFormField<StarCategory>(
            initialValue: _category,
            decoration: const InputDecoration(labelText: "Category", border: OutlineInputBorder()),
            items: [for (final c in StarCategory.values) DropdownMenuItem(value: c, child: Text(c.label))],
            onChanged: (v) => setState(() => _category = v ?? _category),
          ),
          const SizedBox(height: 20),
          if (_completeness != null) _CompletenessCard(completeness: _completeness!),
          const SizedBox(height: 16),
          _StarField(label: "Situation", controller: _situationController),
          _StarField(label: "Task", controller: _taskController),
          _StarField(label: "Action", controller: _actionController),
          _StarField(label: "Result", controller: _resultController),
          const SizedBox(height: 8),
          TextField(controller: _metricsController, decoration: const InputDecoration(labelText: "Metrics (optional)", border: OutlineInputBorder())),
          const SizedBox(height: 16),
          TextField(controller: _lessonsController, maxLines: 2, decoration: const InputDecoration(labelText: "Lessons learned (optional)", border: OutlineInputBorder())),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text("Save"),
          ),
        ],
      ),
    );
  }
}

class _StarField extends StatelessWidget {
  const _StarField({required this.label, required this.controller});

  final String label;
  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: TextField(
        controller: controller,
        maxLines: 3,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
      ),
    );
  }
}

class _CompletenessCard extends StatelessWidget {
  const _CompletenessCard({required this.completeness});

  final StarCompleteness completeness;

  static const _sectionLabels = ["situation", "task", "action", "result"];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("STAR Completeness", style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          for (final section in _sectionLabels)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  SizedBox(width: 90, child: Text(section[0].toUpperCase() + section.substring(1))),
                  Text(_statusLabel(completeness.sections[section] ?? "missing"), style: TextStyle(color: _statusColor(completeness.sections[section] ?? "missing"), fontWeight: FontWeight.w600)),
                ],
              ),
            ),
          if (completeness.gaps.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final gap in completeness.gaps)
              Text("• ${_gapLabel(gap)}", style: const TextStyle(fontSize: 12, color: AppColors.warning)),
          ],
        ],
      ),
    );
  }

  String _statusLabel(String status) => switch (status) {
        "missing" => "Missing",
        "brief" => "Brief",
        "complete" => "Complete",
        "strong" => "Strong",
        _ => status,
      };

  Color _statusColor(String status) => switch (status) {
        "missing" => AppColors.danger,
        "brief" => AppColors.warning,
        "strong" => AppColors.success,
        _ => AppColors.blue,
      };

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
