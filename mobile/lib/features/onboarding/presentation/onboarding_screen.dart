import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/app_providers.dart";
import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";

class _OnboardingPage {
  const _OnboardingPage({required this.icon, required this.tone, required this.title, required this.body, required this.chips});

  final IconData icon;
  final AppTone tone;
  final String title;
  final String body;

  /// Feature labels shown around the illustration — capabilities that exist, not statistics.
  final List<String> chips;
}

const _pages = [
  _OnboardingPage(
    icon: AppIcons.opportunities,
    tone: AppTone.primary,
    title: "Find Better Opportunities",
    body: "Jobs, internships, entry-level roles and scholarships in one place.",
    chips: ["Jobs", "Scholarships"],
  ),
  _OnboardingPage(
    icon: AppIcons.cv,
    tone: AppTone.purple,
    title: "Know Your Career Fit",
    body: "See how your CV reads against a role and what to improve before you apply.",
    chips: ["CV analysis", "Job match"],
  ),
  _OnboardingPage(
    icon: AppIcons.prepare,
    tone: AppTone.success,
    title: "Prepare Smarter",
    body: "Practice aptitude tests and interviews, and build STAR stories that stand out.",
    chips: ["Aptitude", "Interviews"],
  ),
  _OnboardingPage(
    icon: AppIcons.application,
    tone: AppTone.warning,
    title: "Track Your Journey",
    body: "Follow every application from submission to offer.",
    chips: ["Applied", "Interview"],
  ),
];

/// 4-page onboarding flow (master spec §8).
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _finish() async {
    await ref.read(appPreferencesProvider).setOnboardingComplete();
    if (mounted) context.go("/login");
  }

  @override
  Widget build(BuildContext context) {
    final isLastPage = _page == _pages.length - 1;
    final colors = context.colors;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.xs, 0),
              child: Row(
                children: [
                  const CareerOSLogo(markSize: 28),
                  const Spacer(),
                  AnimatedOpacity(
                    opacity: isLastPage ? 0 : 1,
                    duration: AppMotion.of(context, AppMotion.fast),
                    child: TextButton(onPressed: isLastPage ? null : _finish, child: const Text("Skip")),
                  ),
                ],
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (context, i) => _OnboardingPageView(page: _pages[i]),
              ),
            ),
            Semantics(
              label: "Page ${_page + 1} of ${_pages.length}",
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  _pages.length,
                  (i) => AnimatedContainer(
                    duration: AppMotion.of(context),
                    curve: AppMotion.curve,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _page ? 24 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: i == _page ? colors.primary : colors.border,
                      borderRadius: AppRadius.pillAll,
                    ),
                  ),
                ),
              ),
            ),
            if (isLastPage) ...[
              Gap.md,
              Text("Plan. Prepare. Apply. Grow.", style: context.text.labelMedium?.copyWith(color: colors.primary)),
            ],
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.lg, AppSpacing.xl, AppSpacing.xl),
              child: PrimaryButton(
                label: isLastPage ? "Get Started" : "Next",
                icon: isLastPage ? null : Icons.arrow_forward_rounded,
                onPressed: isLastPage
                    ? _finish
                    : () => _controller.nextPage(duration: AppMotion.slow, curve: AppMotion.curve),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingPageView extends StatelessWidget {
  const _OnboardingPageView({required this.page});

  final _OnboardingPage page;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final accent = page.tone.color(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final art = (constraints.maxHeight * 0.42).clamp(160.0, 260.0);
        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ExcludeSemantics(
                  child: SizedBox.square(
                    dimension: art,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(colors: [page.tone.tint(context), colors.background]),
                          ),
                        ),
                        Container(
                          width: art * 0.46,
                          height: art * 0.46,
                          decoration: BoxDecoration(
                            color: colors.surface,
                            borderRadius: BorderRadius.circular(art * 0.14),
                            border: Border.all(color: colors.border),
                            boxShadow: AppShadows.raised(context),
                          ),
                          alignment: Alignment.center,
                          child: Icon(page.icon, size: art * 0.2, color: accent),
                        ),
                        Positioned(
                          left: 0,
                          top: art * 0.2,
                          child: _FloatingChip(label: page.chips[0], tone: page.tone),
                        ),
                        Positioned(
                          right: 0,
                          bottom: art * 0.2,
                          child: _FloatingChip(label: page.chips[1], tone: AppTone.primary),
                        ),
                      ],
                    ),
                  ),
                ),
                Gap.xxl,
                Text(page.title, textAlign: TextAlign.center, style: context.text.headlineMedium),
                Gap.sm,
                Text(page.body, textAlign: TextAlign.center, style: context.text.bodyLarge?.copyWith(color: colors.textSecondary)),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _FloatingChip extends StatelessWidget {
  const _FloatingChip({required this.label, required this.tone});

  final String label;
  final AppTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: AppRadius.pillAll,
        border: Border.all(color: colors.border),
        boxShadow: AppShadows.card(context),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: tone.color(context), shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text(label, style: context.text.labelMedium?.copyWith(color: colors.textPrimary)),
        ],
      ),
    );
  }
}
