import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../data/intelligence_models.dart";
import "intelligence_providers.dart";

/// A single company-intelligence article: what happened, and why it matters to a candidate.
class IntelligenceDetailScreen extends ConsumerWidget {
  const IntelligenceDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(intelligenceDetailProvider(idOrSlug));

    return detailAsync.when(
      loading: () => const DetailSkeleton(),
      error: (error, _) => DetailError(
        title: "We couldn't load this update",
        message: error.userMessage,
        onRetry: () => ref.invalidate(intelligenceDetailProvider(idOrSlug)),
      ),
      data: (post) => _IntelligenceArticle(post: post),
    );
  }
}

class _IntelligenceArticle extends StatelessWidget {
  const _IntelligenceArticle({required this.post});

  final IntelligenceDetail post;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final company = post.company;
    final hasSource = post.sourceUrl != null && post.sourceUrl!.isNotEmpty;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: post.postImageUrl != null ? 220 : 0,
            backgroundColor: colors.background,
            surfaceTintColor: Colors.transparent,
            title: Text("Company Intelligence", style: context.text.titleMedium),
            flexibleSpace: post.postImageUrl == null
                ? null
                : FlexibleSpaceBar(
                    background: ExcludeSemantics(
                      child: CachedNetworkImage(
                        imageUrl: post.postImageUrl!,
                        fit: BoxFit.cover,
                        errorWidget: (_, __, ___) => ColoredBox(color: colors.surfaceMuted),
                      ),
                    ),
                  ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, AppSpacing.xxl),
            sliver: SliverList.list(
              children: [
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [
                    StatusChip(label: humanizeEnum(post.category), tone: AppTone.info),
                    if (post.isVerified) const StatusChip(label: "Verified source", tone: AppTone.success, icon: AppIcons.verified),
                    if (post.isDemo) const StatusChip(label: "DEMO"),
                  ],
                ),
                Gap.sm,
                Semantics(header: true, child: Text(post.headline, style: context.text.headlineSmall)),
                Gap.sm,
                Row(
                  children: [
                    if (company != null) ...[
                      NetworkImageWithFallback(url: company.logoUrl, fallbackText: company.name, size: 28),
                      Gap.xs,
                      Flexible(child: Text(company.name, style: context.text.titleSmall)),
                    ],
                    if (post.publishedAt != null) ...[
                      if (company != null) Text("  ·  ", style: context.text.bodySmall),
                      Text(DateLabels.shortDate(post.publishedAt!), style: context.text.bodySmall),
                    ],
                  ],
                ),
                if (post.sourceName != null) ...[
                  Gap.xxs,
                  Text("Source: ${post.sourceName}", style: context.text.bodySmall),
                ],
                Gap.lg,
                if (post.summary != null && post.fullContent != null) ...[
                  Text(post.summary!, style: context.text.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
                  Gap.md,
                ],
                Text(post.fullContent ?? post.summary ?? "No further detail was provided for this update.", style: context.text.bodyLarge),
                if (post.whyItMatters != null) ...[
                  Gap.xl,
                  CareerCard(
                    color: colors.tint(colors.primary),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.lightbulb_outline_rounded, size: 20, color: colors.primary),
                            Gap.xs,
                            Expanded(child: Text("Why this matters to your career", style: context.text.titleSmall)),
                          ],
                        ),
                        Gap.xs,
                        Text(post.whyItMatters!, style: context.text.bodyLarge),
                        if (post.relevantRoles?.isNotEmpty ?? false) ...[
                          Gap.md,
                          Text("Roles this may affect", style: context.text.labelMedium),
                          Gap.xs,
                          Wrap(
                            spacing: AppSpacing.xs,
                            runSpacing: AppSpacing.xs,
                            children: [for (final role in post.relevantRoles!) TagChip(label: role, tone: AppTone.primary)],
                          ),
                        ],
                        if (post.relevantSkills?.isNotEmpty ?? false) ...[
                          Gap.md,
                          Text("Relevant skills", style: context.text.labelMedium),
                          Gap.xs,
                          Wrap(
                            spacing: AppSpacing.xs,
                            runSpacing: AppSpacing.xs,
                            children: [for (final skill in post.relevantSkills!) TagChip(label: skill)],
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
                if (company != null) ...[
                  Gap.xl,
                  CareerCard(
                    onTap: () => context.push("/companies/${company.slug}"),
                    child: Row(
                      children: [
                        NetworkImageWithFallback(url: company.logoUrl, fallbackText: company.name, size: 44),
                        Gap.sm,
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(company.name, style: context.text.titleSmall),
                              Text("View company profile, jobs and updates", style: context.text.bodySmall),
                            ],
                          ),
                        ),
                        Icon(AppIcons.chevron, color: colors.textSecondary),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: hasSource
          ? BottomActionBar(
              primary: SecondaryButton(
                label: "View original source",
                icon: AppIcons.external,
                onPressed: () => openExternalUrl(context, post.sourceUrl),
              ),
            )
          : null,
    );
  }
}
