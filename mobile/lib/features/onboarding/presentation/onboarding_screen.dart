import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/app_providers.dart";
import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "onboarding_illustrations.dart";

class _OnboardingPage {
  const _OnboardingPage({required this.scene, required this.title, required this.body});

  final OnboardingScene scene;
  final String title;
  final String body;
}

const _pages = [
  _OnboardingPage(
    scene: OnboardingScene.climb,
    title: "Unlock Your Career Potential",
    body: "Jobs, scholarships, company news and career tools — all in one place.",
  ),
  _OnboardingPage(
    scene: OnboardingScene.opportunities,
    title: "Find Opportunities That Fit",
    body: "Search and filter jobs, internships, entry-level roles and scholarships, and save the ones you like.",
  ),
  _OnboardingPage(
    scene: OnboardingScene.prepare,
    title: "Prepare With Confidence",
    body: "Practice aptitude tests and mock interviews, analyze your CV and build STAR stories.",
  ),
  _OnboardingPage(
    scene: OnboardingScene.track,
    title: "Track Every Application",
    body: "Follow each application from applied to offer, with deadlines and recruiter updates in one place.",
  ),
];

/// Illustrated onboarding carousel (mockup board §2). Reached from the welcome screen on first
/// launch, or replayed from Settings (`/onboarding?replay=1`), which returns to where it came from.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key, this.replay = false});

  final bool replay;

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  bool get _isLastPage => _page == _pages.length - 1;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _finish({required String destination}) async {
    await ref.read(appPreferencesProvider).setOnboardingComplete();
    if (!mounted) return;
    if (widget.replay) {
      context.canPop() ? context.pop() : context.go("/home");
    } else {
      context.pushReplacement(destination);
    }
  }

  void _next() => _controller.nextPage(duration: AppMotion.of(context, AppMotion.slow), curve: AppMotion.curve);

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final primaryLabel = _isLastPage ? (widget.replay ? "Done" : "Create Account") : "Next";

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            SizedBox(
              height: 52,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                child: Row(
                  children: [
                    if (context.canPop())
                      IconButton(
                        tooltip: "Back",
                        onPressed: () => _page > 0
                            ? _controller.previousPage(duration: AppMotion.of(context, AppMotion.slow), curve: AppMotion.curve)
                            : context.pop(),
                        icon: const Icon(Icons.arrow_back_rounded),
                      ),
                    const Spacer(),
                    Padding(
                      padding: const EdgeInsets.only(right: AppSpacing.sm),
                      child: Text(
                        "${_page + 1} / ${_pages.length}",
                        style: context.text.labelMedium?.copyWith(color: colors.textSecondary),
                      ),
                    ),
                  ],
                ),
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
                      color: i == _page ? colors.primary : colors.tint(colors.primary),
                      borderRadius: AppRadius.pillAll,
                    ),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.xl, AppSpacing.xl, AppSpacing.xs),
              child: PrimaryButton(
                label: primaryLabel,
                onPressed: _isLastPage ? () => _finish(destination: "/register") : _next,
              ),
            ),
            SizedBox(
              height: 48,
              child: _isLastPage
                  ? (widget.replay
                      ? null
                      : TextButton(
                          onPressed: () => _finish(destination: "/login"),
                          child: const Text("I already have an account"),
                        ))
                  : TextButton(
                      onPressed: () => widget.replay ? _finish(destination: "/home") : _finish(destination: "/register"),
                      style: TextButton.styleFrom(foregroundColor: colors.textSecondary),
                      child: const Text("Skip"),
                    ),
            ),
            Gap.sm,
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
    return LayoutBuilder(
      builder: (context, constraints) {
        final artHeight = (constraints.maxHeight * 0.56).clamp(150.0, 320.0);
        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(height: artHeight, child: OnboardingIllustration(scene: page.scene)),
                Gap.xl,
                Semantics(
                  header: true,
                  child: Text(
                    page.title,
                    textAlign: TextAlign.center,
                    style: context.text.headlineMedium?.copyWith(fontWeight: FontWeight.w800, height: 1.15),
                  ),
                ),
                Gap.sm,
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 340),
                  child: Text(
                    page.body,
                    textAlign: TextAlign.center,
                    style: context.text.bodyLarge?.copyWith(color: colors.textSecondary, height: 1.45),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
