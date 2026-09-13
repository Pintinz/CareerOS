import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
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

enum _MixMode { automatic, custom }

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
  _MixMode _mixMode = _MixMode.automatic;
  final Map<String, int> _customCounts = {};

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

  bool get _isMock => _mode == InterviewSessionMode.mock;
  bool get _isCustomMix => _isMock && _mixMode == _MixMode.custom;

  int get _customMixTotal => _customCounts.values.fold(0, (a, b) => a + b);

  bool get _canStart {
    if (_isCustomMix) return _customMixTotal == _questionCount && _customMixTotal > 0;
    return true;
  }

  Future<void> _start() async {
    final controller = ref.read(interviewSessionCreationControllerProvider.notifier);
    final session = await controller.create(
      mode: _mode,
      categories: _isMock ? const [] : _selectedCategories.toList(),
      categoryCounts: _isCustomMix
          ? (Map.of(_customCounts)..removeWhere((_, count) => count <= 0))
          : null,
      autoMix: _isMock && _mixMode == _MixMode.automatic,
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
                    if (mode == InterviewSessionMode.mock) {
                      _useTimer = true;
                      _mixMode = _MixMode.automatic;
                    }
                  }),
                ),
            ],
          ),
          const SizedBox(height: 20),
          if (_isMock) ...[
            Text("Mock Interview Mix", style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text(
              "Automatic Mix picks a role-appropriate category split for you. Custom Mix lets you set exactly how many questions come from each category.",
              style: TextStyle(color: AppColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  label: const Text("Automatic Mix"),
                  selected: _mixMode == _MixMode.automatic,
                  onSelected: (_) => setState(() => _mixMode = _MixMode.automatic),
                ),
                ChoiceChip(
                  label: const Text("Custom Mix"),
                  selected: _mixMode == _MixMode.custom,
                  onSelected: (_) => setState(() => _mixMode = _MixMode.custom),
                ),
              ],
            ),
            const SizedBox(height: 12),
            categoriesAsync.when(
              loading: () => const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
              error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
              data: (categories) => _mixMode == _MixMode.automatic
                  ? _AutomaticMixPreview(
                      questionCount: _questionCount,
                      applicationId: widget.args.applicationId,
                      jobId: widget.args.jobId,
                    )
                  : _CustomMixBuilder(
                      categories: categories,
                      counts: _customCounts,
                      targetTotal: _questionCount,
                      onChanged: (slug, count) => setState(() {
                        if (count <= 0) {
                          _customCounts.remove(slug);
                        } else {
                          _customCounts[slug] = count;
                        }
                      }),
                    ),
            ),
          ] else ...[
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
          ],
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
          if (_isCustomMix && !_canStart)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _customMixTotal == 0
                    ? "Set at least one category count to start."
                    : "Category counts add up to $_customMixTotal — they need to add up to exactly $_questionCount.",
                style: const TextStyle(color: AppColors.danger, fontSize: 13),
              ),
            ),
          ElevatedButton(
            onPressed: (creationState.isLoading || !_canStart) ? null : _start,
            child: creationState.isLoading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text("Start"),
          ),
        ],
      ),
    );
  }
}

/// Shows what "Automatic Mix" would apply — a real preview from the backend's role-specific
/// default distribution (`GET /interview/sessions/mock-mix-preview`), not a client-side guess.
/// Refetches automatically whenever `questionCount` changes (it's part of the provider's family
/// key) since the split is computed per question count.
class _AutomaticMixPreview extends ConsumerWidget {
  const _AutomaticMixPreview({required this.questionCount, this.applicationId, this.jobId});

  final int questionCount;
  final String? applicationId;
  final String? jobId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final previewAsync = ref.watch(mockMixPreviewProvider(
      MockMixPreviewArgs(questionCount: questionCount, applicationId: applicationId, jobId: jobId),
    ));
    return previewAsync.when(
      loading: () => const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
      error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
      data: (preview) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              preview.source == "role_default" ? "Role-specific split" : "General default split",
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: AppColors.muted),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final entry in preview.categoryCounts.entries)
                  if (entry.value > 0) _Badge(label: "${preview.categoryNames[entry.key] ?? entry.key} ${entry.value}"),
              ],
            ),
            const SizedBox(height: 8),
            Text("Total: ${preview.total}", style: const TextStyle(fontSize: 12, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
      child: Text(label, style: const TextStyle(color: AppColors.blue, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

/// Per-category count steppers for "Custom Mix" — validated by the parent screen to sum to
/// exactly the selected question count before Start is enabled (spec: never silently drop or
/// round a category to zero).
class _CustomMixBuilder extends StatelessWidget {
  const _CustomMixBuilder({
    required this.categories, required this.counts, required this.targetTotal, required this.onChanged,
  });

  final List<InterviewCategory> categories;
  final Map<String, int> counts;
  final int targetTotal;
  final void Function(String slug, int count) onChanged;

  @override
  Widget build(BuildContext context) {
    final total = counts.values.fold(0, (a, b) => a + b);
    final matches = total == targetTotal && total > 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final category in categories)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Expanded(child: Text(category.name)),
                IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  onPressed: (counts[category.slug] ?? 0) > 0
                      ? () => onChanged(category.slug, (counts[category.slug] ?? 0) - 1)
                      : null,
                ),
                SizedBox(width: 24, child: Text("${counts[category.slug] ?? 0}", textAlign: TextAlign.center)),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () => onChanged(category.slug, (counts[category.slug] ?? 0) + 1),
                ),
              ],
            ),
          ),
        const SizedBox(height: 4),
        Text(
          "Total: $total / $targetTotal",
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: matches ? AppColors.success : AppColors.danger,
          ),
        ),
      ],
    );
  }
}
