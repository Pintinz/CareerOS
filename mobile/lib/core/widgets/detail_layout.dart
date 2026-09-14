import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";

import "../design/design.dart";
import "careeros_logo.dart";
import "network_image.dart";
import "state_views.dart";

/// Detail-screen frame (job, scholarship, company, intelligence): collapsing banner hero with an
/// overlapping logo, a header block, pinned underline tabs and one scrollable body per tab.
/// The primary CTA goes in `Scaffold.bottomNavigationBar` via [BottomActionBar].
class DetailScaffold extends StatelessWidget {
  const DetailScaffold({
    super.key,
    required this.title,
    required this.header,
    required this.tabs,
    required this.tabViews,
    this.bannerUrl,
    this.logoUrl,
    this.logoFallbackText,
    this.logoFallbackIcon,
    this.logoTone = AppTone.primary,
    this.actions = const [],
    this.bottomBar,
    this.tabController,
    this.showBanner = true,
  });

  /// Shown in the app bar once the hero collapses.
  final String title;
  final Widget header;
  final List<String> tabs;
  final List<Widget> tabViews;
  final String? bannerUrl;
  final String? logoUrl;

  /// When null (and [logoFallbackIcon] null), no logo is drawn.
  final String? logoFallbackText;
  final IconData? logoFallbackIcon;
  final AppTone logoTone;
  final List<Widget> actions;
  final Widget? bottomBar;
  final TabController? tabController;

  /// False for record screens without imagery (e.g. an application): a plain pinned app bar with
  /// the title, and the header draws its own leading visual.
  final bool showBanner;

  static const double _bannerHeight = 168;
  static const double _logoSize = 72;

  @override
  Widget build(BuildContext context) {
    final hasLogo = showBanner && (logoFallbackText != null || logoFallbackIcon != null);
    final body = NestedScrollView(
      headerSliverBuilder: (context, innerBoxIsScrolled) => [
        SliverOverlapAbsorber(
          handle: NestedScrollView.sliverOverlapAbsorberHandleFor(context),
          sliver: SliverMainAxisGroup(
            slivers: [
              if (!showBanner)
                SliverAppBar(
                  pinned: true,
                  forceElevated: innerBoxIsScrolled,
                  title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
                  actions: actions,
                )
              else
                SliverAppBar(
                  pinned: true,
                  expandedHeight: _bannerHeight + (hasLogo ? _logoSize / 2 : 0),
                  backgroundColor: context.colors.background,
                  surfaceTintColor: Colors.transparent,
                  foregroundColor: Colors.white,
                  title: AnimatedOpacity(
                    opacity: innerBoxIsScrolled ? 1 : 0,
                    duration: AppMotion.of(context, AppMotion.fast),
                    child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.titleMedium),
                  ),
                  leading: const _HeroIconButtonScope(child: BackButton()),
                  actions: [
                    for (final action in actions) _HeroIconButtonScope(child: action),
                    const SizedBox(width: AppSpacing.xxs)
                  ],
                  flexibleSpace: FlexibleSpaceBar(
                    collapseMode: CollapseMode.pin,
                    background: _Banner(
                      url: bannerUrl,
                      bottomBand: hasLogo ? _logoSize / 2 : 0,
                      logo: hasLogo
                          ? Container(
                              padding: const EdgeInsets.all(3),
                              decoration: BoxDecoration(
                                color: context.colors.surface,
                                borderRadius: BorderRadius.circular(AppRadius.feature),
                                boxShadow: AppShadows.raised(context),
                              ),
                              child: NetworkImageWithFallback(
                                url: logoUrl,
                                fallbackText: logoFallbackText ?? title,
                                fallbackIcon: logoFallbackIcon,
                                tone: logoTone,
                                size: _logoSize - 6,
                                radius: AppRadius.card,
                              ),
                            )
                          : null,
                    ),
                  ),
                ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.sm, AppSpacing.pageH, AppSpacing.sm),
                  child: header,
                ),
              ),
              SliverPersistentHeader(
                pinned: true,
                delegate: _PinnedTabBarDelegate(
                  TabBar(
                    controller: tabController,
                    isScrollable: tabs.length > 3,
                    tabAlignment: tabs.length > 3 ? TabAlignment.start : TabAlignment.fill,
                    tabs: [for (final t in tabs) Tab(text: t)],
                  ),
                  background: context.colors.background,
                ),
              ),
            ],
          ),
        ),
      ],
      body: TabBarView(
        controller: tabController,
        children: [for (final view in tabViews) _TabBody(child: view)],
      ),
    );

    return Scaffold(
      body: tabController == null ? DefaultTabController(length: tabs.length, child: body) : body,
      bottomNavigationBar: bottomBar,
    );
  }
}

/// Icon buttons over the banner sit on a translucent disc so they stay legible on any image.
class _HeroIconButtonScope extends StatelessWidget {
  const _HeroIconButtonScope({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(6),
      child: DecoratedBox(
        decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.28), shape: BoxShape.circle),
        child: IconTheme.merge(data: const IconThemeData(color: Colors.white), child: child),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({this.url, this.logo, this.bottomBand = 0});

  final String? url;
  final Widget? logo;

  /// Height of the plain band under the image that the logo straddles.
  final double bottomBand;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final brandGround = DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colors.heroGradient),
      ),
      child: const Align(
        alignment: Alignment(0.85, 0.2),
        child: Opacity(opacity: 0.16, child: CareerOSMark(size: 120, onDark: true, decorative: true)),
      ),
    );
    return ColoredBox(
      color: colors.background,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned.fill(
            bottom: bottomBand,
            child: ExcludeSemantics(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (url == null || url!.isEmpty)
                    brandGround
                  else
                    CachedNetworkImage(
                      imageUrl: url!,
                      fit: BoxFit.cover,
                      placeholder: (_, __) => brandGround,
                      errorWidget: (_, __, ___) => brandGround,
                    ),
                  // Top scrim keeps the back/actions legible over bright photos.
                  const DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.center,
                        colors: [Color(0x66000000), Color(0x00000000)],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (logo != null) Positioned(left: AppSpacing.pageH, bottom: 0, child: logo!),
        ],
      ),
    );
  }
}

class _PinnedTabBarDelegate extends SliverPersistentHeaderDelegate {
  _PinnedTabBarDelegate(this.tabBar, {required this.background});

  final TabBar tabBar;
  final Color background;

  @override
  double get minExtent => tabBar.preferredSize.height;

  @override
  double get maxExtent => tabBar.preferredSize.height;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) =>
      ColoredBox(color: background, child: tabBar);

  @override
  bool shouldRebuild(_PinnedTabBarDelegate oldDelegate) =>
      oldDelegate.tabBar != tabBar || oldDelegate.background != background;
}

/// Each tab scrolls independently beneath the pinned header.
class _TabBody extends StatelessWidget {
  const _TabBody({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Builder(
      builder: (context) => CustomScrollView(
        key: PageStorageKey<Widget>(child),
        slivers: [
          SliverOverlapInjector(handle: NestedScrollView.sliverOverlapAbsorberHandleFor(context)),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.lg, AppSpacing.pageH, AppSpacing.xxl),
            sliver: SliverToBoxAdapter(child: child),
          ),
        ],
      ),
    );
  }
}

/// Titled content block inside a detail tab.
class DetailSection extends StatelessWidget {
  const DetailSection({super.key, required this.title, required this.child, this.icon});

  final String title;
  final Widget child;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (icon != null) ...[Icon(icon, size: 20, color: context.colors.primary), Gap.xs],
              Expanded(child: Semantics(header: true, child: Text(title, style: context.text.titleMedium))),
            ],
          ),
          Gap.sm,
          child,
        ],
      ),
    );
  }
}

/// Bulleted list; `checked` renders green check marks (coverage, benefits).
class BulletList extends StatelessWidget {
  const BulletList({super.key, required this.items, this.checked = false});

  final List<String> items;
  final bool checked;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (checked)
                  const Padding(
                    padding: EdgeInsets.only(top: 1),
                    child: Icon(Icons.check_circle_rounded, size: 18, color: AppColors.success),
                  )
                else
                  Padding(
                    padding: const EdgeInsets.only(top: 8, left: 4, right: 4),
                    child: Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(color: context.colors.primary, shape: BoxShape.circle)),
                  ),
                Gap.xs,
                Expanded(child: Text(item, style: context.text.bodyLarge)),
              ],
            ),
          ),
      ],
    );
  }
}

/// Label/value fact row for key details (salary, deadline, headquarters...).
class FactRow extends StatelessWidget {
  const FactRow({super.key, required this.icon, required this.label, required this.value, this.valueColor});

  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          Icon(icon, size: 20, color: context.colors.textSecondary),
          Gap.sm,
          Expanded(child: Text(label, style: context.text.bodyMedium)),
          Gap.sm,
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: context.text.titleSmall?.copyWith(color: valueColor),
            ),
          ),
        ],
      ),
    );
  }
}

/// Loading placeholder for detail screens (banner + title lines).
class DetailSkeleton extends StatelessWidget {
  const DetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(),
      body: const Padding(
        padding: AppSpacing.page,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LoadingSkeleton(width: double.infinity, height: 140, radius: AppRadius.feature),
            Gap.lg,
            LoadingSkeleton(width: 72, height: 72, radius: AppRadius.card),
            Gap.md,
            LoadingSkeleton(width: 240, height: 24),
            Gap.xs,
            LoadingSkeleton(width: 160, height: 16),
            Gap.lg,
            LoadingSkeleton(width: double.infinity, height: 14),
            Gap.xs,
            LoadingSkeleton(width: double.infinity, height: 14),
            Gap.xs,
            LoadingSkeleton(width: 200, height: 14),
          ],
        ),
      ),
    );
  }
}

/// Error frame for detail screens.
class DetailError extends StatelessWidget {
  const DetailError(
      {super.key, required this.message, required this.onRetry, this.title = "We couldn't load this page"});

  final String title;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(appBar: AppBar(), body: ErrorState(title: title, message: message, onRetry: onRetry));
  }
}
