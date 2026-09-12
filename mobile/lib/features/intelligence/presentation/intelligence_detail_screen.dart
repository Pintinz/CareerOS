import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../theme/app_colors.dart";
import "intelligence_providers.dart";

class IntelligenceDetailScreen extends ConsumerWidget {
  const IntelligenceDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(intelligenceDetailProvider(idOrSlug));

    return Scaffold(
      appBar: AppBar(title: const Text("Company Intelligence")),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(error.userMessage, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => ref.invalidate(intelligenceDetailProvider(idOrSlug)),
                  child: const Text("Retry"),
                ),
              ],
            ),
          ),
        ),
        data: (post) => SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (post.postImageUrl != null)
                CachedNetworkImage(
                  imageUrl: post.postImageUrl!,
                  width: double.infinity,
                  height: 200,
                  fit: BoxFit.cover,
                  errorWidget: (context, url, error) => const SizedBox.shrink(),
                ),
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.purple.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        post.category.replaceAll("_", " "),
                        style: const TextStyle(fontSize: 11, color: AppColors.purple, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(post.headline, style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        if (post.company != null) Text(post.company!.name, style: Theme.of(context).textTheme.titleLarge),
                        if (post.publishedAt != null) ...[
                          if (post.company != null) const Text("  ·  ", style: TextStyle(color: AppColors.muted)),
                          Text(DateFormat.yMMMd().format(post.publishedAt!), style: Theme.of(context).textTheme.bodyMedium),
                        ],
                      ],
                    ),
                    const SizedBox(height: 20),
                    Text(
                      post.fullContent ?? post.summary ?? "No content provided.",
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    if (post.whyItMatters != null) ...[
                      const SizedBox(height: 24),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.blue.withValues(alpha: 0.06),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.lightbulb_outline, size: 18, color: AppColors.blue),
                                SizedBox(width: 6),
                                Text("Why This Matters To Your Career", style: TextStyle(fontWeight: FontWeight.w700)),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(post.whyItMatters!),
                            if (post.relevantRoles?.isNotEmpty ?? false) ...[
                              const SizedBox(height: 10),
                              Text("Potentially impacted roles: ${post.relevantRoles!.join(", ")}",
                                  style: const TextStyle(fontSize: 12, color: AppColors.muted)),
                            ],
                            if (post.relevantSkills?.isNotEmpty ?? false) ...[
                              const SizedBox(height: 4),
                              Text("Relevant skills: ${post.relevantSkills!.join(", ")}",
                                  style: const TextStyle(fontSize: 12, color: AppColors.muted)),
                            ],
                          ],
                        ),
                      ),
                    ],
                    if (post.sourceUrl != null) ...[
                      const SizedBox(height: 20),
                      OutlinedButton.icon(
                        onPressed: () => openExternalUrl(context, post.sourceUrl),
                        icon: const Icon(Icons.open_in_new, size: 16),
                        label: Text(post.isVerified ? "View original source (verified)" : "View original source"),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
