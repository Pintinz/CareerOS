import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
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
const _kDifficultyLabels = {"EASY": "Easy", "MEDIUM": "Medium", "HARD": "Hard", "MIXED": "Mixed"};

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
      categoryCounts: _isCustomMix ? (Map.of(_customCounts)..removeWhere((_, count) => count <= 0)) : null,
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
    final colors = context.colors;
    final categoriesAsync = ref.watch(interviewCategoriesProvider);
    final creationState = ref.watch(interviewSessionCreationControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Set Up Interview Practice")),
      bottomNavigationBar: BottomActionBar(
        caption: Text(
          ["$_questionCount questions", _kDifficultyLabels[_difficulty]!, if (_useTimer) "${_timePerQuestionSeconds}s each"].join(" · "),
        ),
        primary: PrimaryButton(
          label: "Start Practice",
          isLoading: creationState.isLoading,
          onPressed: _canStart ? _start : null,
        ),
      ),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          _ConfigSection(
            title: "Mode",
            child: Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: [
                for (final mode in InterviewSessionMode.values)
                  ChoiceChip(
                    label: Text(mode.label),
                    selected: _mode == mode,
                    selectedColor: colors.primary,
                    labelStyle: context.text.labelMedium?.copyWith(color: _mode == mode ? Colors.white : colors.textPrimary),
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
          ),
          if (_isMock)
            _ConfigSection(
              title: "Mock Interview Mix",
              subtitle:
                  "Automatic Mix picks a role-appropriate category split for you. Custom Mix lets you set exactly how many questions come from each category.",
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: AppSpacing.xs,
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
                  Gap.sm,
                  categoriesAsync.when(
                    loading: () => const LoadingSkeleton(height: 40),
                    error: (e, _) => Text(e.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
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
                ],
              ),
            )
          else
            _ConfigSection(
              title: "Categories",
              subtitle: "Leave all unselected for a mixed session across every category.",
              child: categoriesAsync.when(
                loading: () => const LoadingSkeleton(height: 36, radius: AppRadius.pill),
                error: (e, _) => Text(e.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
                data: (categories) => Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [
                    for (final category in categories)
                      FilterChip(
                        label: Text(category.name),
                        selected: _selectedCategories.contains(category.slug),
                        showCheckmark: true,
                        checkmarkColor: colors.primary,
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
            ),
          _ConfigSection(
            title: "Difficulty",
            child: SizedBox(
              width: double.infinity,
              child: SegmentedButton<String>(
                showSelectedIcon: false,
                segments: [for (final e in _kDifficultyLabels.entries) ButtonSegment(value: e.key, label: Text(e.value))],
                selected: {_difficulty},
                onSelectionChanged: (v) => setState(() => _difficulty = v.first),
              ),
            ),
          ),
          _ConfigSection(
            title: "Number of Questions",
            child: SizedBox(
              width: double.infinity,
              child: SegmentedButton<int>(
                showSelectedIcon: false,
                segments: [for (final count in _kQuestionCounts) ButtonSegment(value: count, label: Text("$count"))],
                selected: {_questionCount},
                onSelectionChanged: (v) => setState(() => _questionCount = v.first),
              ),
            ),
          ),
          _ConfigSection(
            title: "Time per question",
            trailing: Switch(value: _useTimer, onChanged: (v) => setState(() => _useTimer = v)),
            child: _useTimer
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Self-paced timer for reference only — nothing is auto-submitted when it runs out.", style: context.text.bodySmall),
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
                          SizedBox(width: 50, child: Text("${_timePerQuestionSeconds}s", textAlign: TextAlign.end, style: context.text.titleSmall)),
                        ],
                      ),
                    ],
                  )
                : Text("Off — answer at your own pace.", style: context.text.bodySmall),
          ),
          if (creationState.hasError)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Text(creationState.error!.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
            ),
          if (_isCustomMix && !_canStart)
            Text(
              _customMixTotal == 0
                  ? "Set at least one category count to start."
                  : "Category counts add up to $_customMixTotal — they need to add up to exactly $_questionCount.",
              style: context.text.bodyMedium?.copyWith(color: AppColors.error),
            ),
        ],
      ),
    );
  }
}

class _ConfigSection extends StatelessWidget {
  const _ConfigSection({required this.title, required this.child, this.subtitle, this.trailing});

  final String title;
  final String? subtitle;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: CareerCard(
        variant: CareerCardVariant.outlined,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(title, style: context.text.titleMedium)),
                if (trailing != null) trailing!,
              ],
            ),
            if (subtitle != null) ...[const SizedBox(height: 2), Text(subtitle!, style: context.text.bodySmall)],
            Gap.sm,
            child,
          ],
        ),
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
      loading: () => const LoadingSkeleton(height: 40),
      error: (e, _) => Text(e.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
      data: (preview) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.sm),
        decoration: BoxDecoration(color: context.colors.surfaceMuted, borderRadius: AppRadius.mdAll),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(preview.source == "role_default" ? "Role-specific split" : "General default split", style: context.text.labelMedium),
            Gap.xs,
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: [
                for (final entry in preview.categoryCounts.entries)
                  if (entry.value > 0)
                    TagChip(label: "${preview.categoryNames[entry.key] ?? entry.key} ${entry.value}", tone: AppTone.primary),
              ],
            ),
            Gap.xs,
            Text("Total: ${preview.total}", style: context.text.bodySmall),
          ],
        ),
      ),
    );
  }
}

/// Per-category count steppers for "Custom Mix" — validated by the parent screen to sum to
/// exactly the selected question count before Start is enabled (spec: never silently drop or
/// round a category to zero).
class _CustomMixBuilder extends StatelessWidget {
  const _CustomMixBuilder({required this.categories, required this.counts, required this.targetTotal, required this.onChanged});

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
          Row(
            children: [
              Expanded(child: Text(category.name, style: context.text.bodyLarge)),
              IconButton(
                tooltip: "Fewer ${category.name} questions",
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: (counts[category.slug] ?? 0) > 0 ? () => onChanged(category.slug, (counts[category.slug] ?? 0) - 1) : null,
              ),
              SizedBox(width: 28, child: Text("${counts[category.slug] ?? 0}", textAlign: TextAlign.center, style: context.text.titleSmall)),
              IconButton(
                tooltip: "More ${category.name} questions",
                icon: Icon(Icons.add_circle_outline, color: context.colors.primary),
                onPressed: () => onChanged(category.slug, (counts[category.slug] ?? 0) + 1),
              ),
            ],
          ),
        Gap.xs,
        StatusChip(
          label: "Total: $total / $targetTotal",
          tone: matches ? AppTone.success : AppTone.danger,
          icon: matches ? AppIcons.check : Icons.info_outline_rounded,
        ),
      ],
    );
  }
}
