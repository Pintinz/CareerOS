import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/monetization/ad_placement.dart";
import "../../../core/monetization/monetization_models.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/monetization/widgets/rewarded_unlock_dialog.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
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
    // Soft gate (spec §14-15): the daily free limit is informational here — backend doesn't hard-
    // block session creation yet (see PROJECT_STATUS.md's Phase 10 scoping note), but the app
    // still offers the intended rewarded-unlock flow at the natural point, never blocking a user
    // who has no more free sessions from at least being offered a path forward.
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

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(questionCategoriesProvider);
    final creationState = ref.watch(sessionCreationControllerProvider);
    final isPracticeWeakAreas = widget.args.topicSlugs != null;
    // Watched (not just read in _start()) so it's resolved well before the user can tap Start —
    // the rewarded-unlock soft gate reads the fully-settled value, never a still-loading one.
    ref.watch(entitlementProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Configure Test")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (isPracticeWeakAreas)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
              child: const Text(
                "This session is weighted toward your weakest topics based on your past results.",
                style: TextStyle(fontSize: 13),
              ),
            ),
          Text("Test Mode", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final mode in [TestMode.practice, TestMode.timed, TestMode.mock, TestMode.jobSpecific, TestMode.fieldSpecific])
                ChoiceChip(
                  label: Text(mode.label),
                  selected: _mode == mode,
                  onSelected: (_) => setState(() {
                    _mode = mode;
                    if (mode == TestMode.timed || mode == TestMode.mock) _timing = "OVERALL";
                  }),
                ),
            ],
          ),
          if (_mode == TestMode.jobSpecific || _mode == TestMode.fieldSpecific) ...[
            const SizedBox(height: 20),
            Text("Base this on which application?", style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text(
              "Technical questions are weighted toward that role's field and industry.",
              style: TextStyle(color: AppColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 8),
            _ApplicationPicker(
              selectedId: _selectedApplicationId,
              onChanged: (id) => setState(() => _selectedApplicationId = id),
            ),
          ],
          if (!isPracticeWeakAreas) ...[
            const SizedBox(height: 20),
            Text("Sections", style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text("Leave all unselected for a mixed test across every section.", style: TextStyle(color: AppColors.muted, fontSize: 13)),
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
                      selected: _selectedSections.contains(category.slug),
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
          Text("Timing", style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          if (_mode == TestMode.timed || _mode == TestMode.mock)
            const Text("Timed and Mock Assessment modes require a timer.", style: TextStyle(color: AppColors.muted, fontSize: 13)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text("Untimed"),
                selected: _timing == "UNTIMED",
                onSelected: (_mode == TestMode.timed || _mode == TestMode.mock)
                    ? null
                    : (_) => setState(() => _timing = "UNTIMED"),
              ),
              ChoiceChip(
                label: const Text("Overall Timer"),
                selected: _timing == "OVERALL",
                onSelected: (_) => setState(() => _timing = "OVERALL"),
              ),
            ],
          ),
          if (_timing == "OVERALL") ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const Text("Time limit:"),
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
                SizedBox(width: 56, child: Text("$_timeLimitMinutes min", textAlign: TextAlign.end)),
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
                : const Text("Start Test"),
          ),
        ],
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
      return const Text(
        "No tracked applications yet — this session will use general questions for the selected sections.",
        style: TextStyle(color: AppColors.muted, fontSize: 13),
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
