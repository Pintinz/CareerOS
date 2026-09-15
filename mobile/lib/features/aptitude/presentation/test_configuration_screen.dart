import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/monetization/ad_placement.dart";
import "../../../core/monetization/monetization_models.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/monetization/widgets/rewarded_unlock_dialog.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../../applications/presentation/application_providers.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";

/// Arguments for launching the configuration screen with preselected context — from the
/// Preparation Hub (no context) or from an application's "Prepare for Aptitude Test" button
/// (application/job context preselected, spec §38).
class AptitudeConfigureArgs {
  const AptitudeConfigureArgs({this.initialMode = TestMode.practice, this.applicationId, this.topicSlugs});

  final TestMode initialMode;
  final String? applicationId;
  /// Set only for the "Practice Weak Areas" entry point (spec §27) — restricts generation to
  /// these specific topics regardless of section/mode selection.
  final List<String>? topicSlugs;
}

const _kQuestionCounts = [10, 20, 30, 40, 60];
const _kDifficultyLabels = {"EASY": "Easy", "MEDIUM": "Medium", "HARD": "Hard", "MIXED": "Mixed"};

class TestConfigurationScreen extends ConsumerStatefulWidget {
  const TestConfigurationScreen({super.key, required this.args});

  final AptitudeConfigureArgs args;

  @override
  ConsumerState<TestConfigurationScreen> createState() => _TestConfigurationScreenState();
}

class _TestConfigurationScreenState extends ConsumerState<TestConfigurationScreen> {
  late TestMode _mode;
  final Set<String> _selectedSections = {};
  String _difficulty = "MIXED";
  int _questionCount = 20;
  String _timing = "UNTIMED";
  int _timeLimitMinutes = 30;
  String? _selectedApplicationId;

  @override
  void initState() {
    super.initState();
    _mode = widget.args.initialMode;
    _selectedApplicationId = widget.args.applicationId;
    if (_mode == TestMode.timed || _mode == TestMode.mock) {
      _timing = "OVERALL";
    }
    if (widget.args.topicSlugs != null) {
      // Practice Weak Areas: sections are irrelevant — topic_slugs alone drives generation.
      _questionCount = 20;
    }
  }

  Future<void> _start() async {
    // Soft gate (spec §14-15): offer the rewarded-unlock flow at the natural point when today's
    // free sessions are used up; the backend enforces the real limit.
    final entitlement = ref.read(entitlementProvider).valueOrNull;
    if (entitlement != null && entitlement.aptitudeLimitReached) {
      final unlocked = await showRewardedUnlockDialog(
        context,
        title: "Daily free limit reached",
        message: "You've used today's free aptitude tests. Want another practice session?",
        placement: AdPlacement.aptitudeUnlock,
        rewardType: RewardType.extraAptitudeTest,
      );
      if (!unlocked) return;
      ref.invalidate(entitlementProvider);
    }

    final controller = ref.read(sessionCreationControllerProvider.notifier);
    final needsJobContext = _mode == TestMode.jobSpecific || _mode == TestMode.fieldSpecific;
    final session = await controller.create(
      mode: _mode,
      sections: _selectedSections.toList(),
      difficulty: _difficulty,
      questionCount: _questionCount,
      timing: _timing,
      timeLimitMinutes: _timing == "OVERALL" ? _timeLimitMinutes : null,
      applicationId: needsJobContext ? _selectedApplicationId : widget.args.applicationId,
      topicSlugs: widget.args.topicSlugs,
    );
    if (session != null && mounted) {
      context.pushReplacement("/prepare/aptitude/sessions/${session.id}");
    }
  }

  static String _modeDescription(TestMode mode) => switch (mode) {
        TestMode.practice => "Learn at your own pace, then review every answer.",
        TestMode.timed => "Work against the clock to build speed and accuracy.",
        TestMode.mock => "A full assessment under exam-like conditions.",
        TestMode.jobSpecific => "Technical questions weighted toward a role you're applying for.",
        TestMode.fieldSpecific => "Questions weighted toward an application's field and industry.",
        TestMode.companySpecific => "Questions shaped around a specific employer.",
      };

  static IconData _modeIcon(TestMode mode) => switch (mode) {
        TestMode.practice => Icons.school_outlined,
        TestMode.timed => AppIcons.timer,
        TestMode.mock => Icons.assignment_outlined,
        TestMode.jobSpecific => AppIcons.job,
        TestMode.fieldSpecific => Icons.category_outlined,
        TestMode.companySpecific => AppIcons.company,
      };

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final categoriesAsync = ref.watch(questionCategoriesProvider);
    final creationState = ref.watch(sessionCreationControllerProvider);
    final isPracticeWeakAreas = widget.args.topicSlugs != null;
    final timerForced = _mode == TestMode.timed || _mode == TestMode.mock;
    // Watched (not just read in _start()) so it's resolved well before the user can tap Start —
    // the rewarded-unlock soft gate reads the fully-settled value, never a still-loading one.
    ref.watch(entitlementProvider);

    final summary = [
      "$_questionCount questions",
      _kDifficultyLabels[_difficulty]!,
      _timing == "OVERALL" ? "$_timeLimitMinutes min" : "Untimed",
    ].join(" · ");

    return Scaffold(
      appBar: AppBar(title: const Text("Set Up Assessment")),
      bottomNavigationBar: BottomActionBar(
        caption: Text(summary),
        primary: PrimaryButton(label: "Start Assessment", isLoading: creationState.isLoading, onPressed: _start),
      ),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          if (isPracticeWeakAreas) ...[
            const InsightCard(
              icon: Icons.track_changes_rounded,
              tone: AppTone.purple,
              title: "Practice Weak Areas",
              message: "This session is weighted toward your weakest topics based on your past results.",
            ),
            Gap.lg,
          ],
          _ConfigSection(
            title: "Test Mode",
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [
                    for (final mode in const [TestMode.practice, TestMode.timed, TestMode.mock, TestMode.jobSpecific, TestMode.fieldSpecific])
                      ChoiceChip(
                        avatar: Icon(_modeIcon(mode), size: 16, color: _mode == mode ? Colors.white : colors.textSecondary),
                        label: Text(mode.label),
                        selected: _mode == mode,
                        selectedColor: colors.primary,
                        labelStyle: context.text.labelMedium?.copyWith(color: _mode == mode ? Colors.white : colors.textPrimary),
                        onSelected: (_) => setState(() {
                          _mode = mode;
                          if (mode == TestMode.timed || mode == TestMode.mock) _timing = "OVERALL";
                        }),
                      ),
                  ],
                ),
                Gap.sm,
                AnimatedSwitcher(
                  duration: AppMotion.of(context, AppMotion.fast),
                  child: Text(_modeDescription(_mode), key: ValueKey(_mode), style: context.text.bodySmall),
                ),
                if (_mode == TestMode.jobSpecific || _mode == TestMode.fieldSpecific) ...[
                  Gap.md,
                  Text("Base this on which application?", style: context.text.titleSmall),
                  const SizedBox(height: 2),
                  Text("Technical questions are weighted toward that role's field and industry.", style: context.text.bodySmall),
                  Gap.xs,
                  _ApplicationPicker(
                    selectedId: _selectedApplicationId,
                    onChanged: (id) => setState(() => _selectedApplicationId = id),
                  ),
                ],
              ],
            ),
          ),
          if (!isPracticeWeakAreas)
            _ConfigSection(
              title: "Sections",
              subtitle: "Leave all unselected for a mixed test across every section.",
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
                        selected: _selectedSections.contains(category.slug),
                        showCheckmark: true,
                        checkmarkColor: colors.primary,
                        onSelected: (selected) => setState(() {
                          if (selected) {
                            _selectedSections.add(category.slug);
                          } else {
                            _selectedSections.remove(category.slug);
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
                segments: [
                  for (final entry in _kDifficultyLabels.entries) ButtonSegment(value: entry.key, label: Text(entry.value)),
                ],
                selected: {_difficulty},
                onSelectionChanged: (value) => setState(() => _difficulty = value.first),
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
                onSelectionChanged: (value) => setState(() => _questionCount = value.first),
              ),
            ),
          ),
          _ConfigSection(
            title: "Timing",
            subtitle: timerForced ? "Timed and Mock Assessment modes require a timer." : null,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpacing.xs,
                  children: [
                    ChoiceChip(
                      label: const Text("Untimed"),
                      selected: _timing == "UNTIMED",
                      onSelected: timerForced ? null : (_) => setState(() => _timing = "UNTIMED"),
                    ),
                    ChoiceChip(
                      avatar: const Icon(AppIcons.timer, size: 16),
                      label: const Text("Overall Timer"),
                      selected: _timing == "OVERALL",
                      onSelected: (_) => setState(() => _timing = "OVERALL"),
                    ),
                  ],
                ),
                if (_timing == "OVERALL") ...[
                  Gap.sm,
                  Row(
                    children: [
                      Text("Time limit", style: context.text.bodyMedium),
                      Expanded(
                        child: Slider(
                          value: _timeLimitMinutes.toDouble(),
                          min: 5,
                          max: 90,
                          divisions: 17,
                          label: "$_timeLimitMinutes min",
                          onChanged: (value) => setState(() => _timeLimitMinutes = value.round()),
                        ),
                      ),
                      SizedBox(
                        width: 60,
                        child: Text("$_timeLimitMinutes min", textAlign: TextAlign.end, style: context.text.titleSmall),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          if (creationState.hasError)
            Text(creationState.error!.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
        ],
      ),
    );
  }
}

class _ConfigSection extends StatelessWidget {
  const _ConfigSection({required this.title, required this.child, this.subtitle});

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: CareerCard(
        variant: CareerCardVariant.outlined,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: context.text.titleMedium),
            if (subtitle != null) ...[const SizedBox(height: 2), Text(subtitle!, style: context.text.bodySmall)],
            Gap.sm,
            child,
          ],
        ),
      ),
    );
  }
}

class _ApplicationPicker extends ConsumerWidget {
  const _ApplicationPicker({required this.selectedId, required this.onChanged});

  final String? selectedId;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listState = ref.watch(applicationListProvider);
    if (listState.items.isEmpty) {
      return Text(
        "No tracked applications yet — this session will use general questions for the selected sections.",
        style: context.text.bodySmall,
      );
    }
    return DropdownButtonFormField<String>(
      initialValue: selectedId,
      isExpanded: true,
      hint: const Text("General (no specific application)"),
      items: [
        const DropdownMenuItem(value: null, child: Text("General (no specific application)")),
        for (final application in listState.items)
          DropdownMenuItem(value: application.id, child: Text("${application.roleTitle} at ${application.companyName}")),
      ],
      onChanged: onChanged,
    );
  }
}
