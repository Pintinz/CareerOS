import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../data/interview_models.dart";
import "interview_providers.dart";

/// Arguments for launching the configuration screen — from the Interview Home hub (a single
/// category preselected, or none for a general mixed session) or from an application's "Prepare
/// for Interview" / "Continue Preparation" button (application/job/company context preselected).
class InterviewConfigureArgs {
  const InterviewConfigureArgs({
    this.initialMode = InterviewSessionMode.practice,
    this.initialCategorySlug,
    this.applicationId,
    this.jobId,
    this.companyId,
  });

  final InterviewSessionMode initialMode;
  final String? initialCategorySlug;
  final String? applicationId;
  final String? jobId;
  final String? companyId;
}

const _kQuestionCounts = [5, 10, 15, 20];

class InterviewConfigurationScreen extends ConsumerStatefulWidget {
  const InterviewConfigurationScreen({super.key, required this.args});

  final InterviewConfigureArgs args;

  @override
  ConsumerState<InterviewConfigurationScreen> createState() => _InterviewConfigurationScreenState();
}

class _InterviewConfigurationScreenState extends ConsumerState<InterviewConfigurationScreen> {
  late InterviewSessionMode _mode;
  final Set<String> _selectedCategories = {};
  String _difficulty = "MIXED";
  int _questionCount = 10;
  bool _useTimer = false;
  int _timePerQuestionSeconds = 120;

  @override
  void initState() {
    super.initState();
    _mode = widget.args.initialMode;
    if (widget.args.initialCategorySlug != null) {
      _selectedCategories.add(widget.args.initialCategorySlug!);
    }
    if (_mode == InterviewSessionMode.mock) {
      _useTimer = true;
    }
  }

  Future<void> _start() async {
    final controller = ref.read(interviewSessionCreationControllerProvider.notifier);
    final session = await controller.create(
      mode: _mode,
      categories: _selectedCategories.toList(),
      difficulty: _difficulty,
      questionCount: _questionCount,
      timePerQuestionSeconds: _useTimer ? _timePerQuestionSeconds : null,
      applicationId: widget.args.applicationId,
      jobId: widget.args.jobId,
      companyId: widget.args.companyId,
    );
    if (session != null && mounted) {
      context.pushReplacement("/prepare/interview/sessions/${session.id}");
    }
  }

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(interviewCategoriesProvider);
    final creationState = ref.watch(interviewSessionCreationControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Configure Interview Practice")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text("Mode", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final mode in InterviewSessionMode.values)
                ChoiceChip(
                  label: Text(mode.label),
                  selected: _mode == mode,
                  onSelected: (_) => setState(() {
                    _mode = mode;
                    if (mode == InterviewSessionMode.mock) _useTimer = true;
                  }),
                ),
            ],
          ),
          const SizedBox(height: 20),
          Text("Categories", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          const Text("Leave all unselected for a mixed session across every category.", style: TextStyle(color: AppColors.muted, fontSize: 13)),
          const SizedBox(height: 8),
          categoriesAsync.when(
            loading: () => const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
            error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
            data: (categories) => Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final category in categories)
                  FilterChip(
                    label: Text(category.name),
                    selected: _selectedCategories.contains(category.slug),
                    onSelected: (selected) => setState(() {
                      if (selected) {
                        _selectedCategories.add(category.slug);
                      } else {
                        _selectedCategories.remove(category.slug);
                      }
                    }),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text("Difficulty", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final entry in const {"EASY": "Easy", "MEDIUM": "Medium", "HARD": "Hard", "MIXED": "Mixed"}.entries)
                ChoiceChip(
                  label: Text(entry.value),
                  selected: _difficulty == entry.key,
                  onSelected: (_) => setState(() => _difficulty = entry.key),
                ),
            ],
          ),
          const SizedBox(height: 20),
          Text("Number of Questions", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final count in _kQuestionCounts)
                ChoiceChip(
                  label: Text("$count"),
                  selected: _questionCount == count,
                  onSelected: (_) => setState(() => _questionCount = count),
                ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(child: Text("Time per question", style: Theme.of(context).textTheme.titleMedium)),
              Switch(value: _useTimer, onChanged: (v) => setState(() => _useTimer = v)),
            ],
          ),
          if (_useTimer) ...[
            const Text("Self-paced timer for reference only — nothing is auto-submitted when it runs out.", style: TextStyle(color: AppColors.muted, fontSize: 12)),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: _timePerQuestionSeconds.toDouble(),
                    min: 30,
                    max: 300,
                    divisions: 9,
                    label: "${_timePerQuestionSeconds}s",
                    onChanged: (v) => setState(() => _timePerQuestionSeconds = v.round()),
                  ),
                ),
                SizedBox(width: 50, child: Text("${_timePerQuestionSeconds}s", textAlign: TextAlign.end)),
              ],
            ),
          ],
          const SizedBox(height: 28),
          if (creationState.hasError)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(creationState.error!.userMessage, style: const TextStyle(color: AppColors.danger)),
            ),
          ElevatedButton(
            onPressed: creationState.isLoading ? null : _start,
            child: creationState.isLoading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text("Start"),
          ),
        ],
      ),
    );
  }
}
