import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "interview_providers.dart";

/// Company + role preparation for an application-linked interview (spec §9/§26/§27): company
/// overview, recent developments, likely topics, a persisted research checklist, and a curated
/// "questions to ask the interviewer" module.
class CompanyPrepScreen extends ConsumerWidget {
  const CompanyPrepScreen({super.key, required this.applicationId});

  final String applicationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prepAsync = ref.watch(companyPrepProvider(applicationId));
    final progressAsync = ref.watch(preparationProgressProvider(applicationId));

    return Scaffold(
      appBar: AppBar(title: const Text("Company Preparation")),
      body: prepAsync.when(
        loading: () => const SkeletonList(itemCount: 3),
        error: (e, _) => ErrorState(
          title: "We couldn't load company preparation",
          message: e.userMessage,
          onRetry: () => ref.invalidate(companyPrepProvider(applicationId)),
        ),
        data: (prep) => ListView(
          padding: AppSpacing.page,
          children: [
            Row(
              children: [
                NetworkImageWithFallback(url: null, fallbackText: prep.companyName ?? "Company", size: 52),
                Gap.md,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(prep.companyName ?? "Company", style: context.text.headlineSmall),
                      if (prep.industry != null) Text(prep.industry!, style: context.text.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
            Gap.md,
            InsightCard(icon: Icons.info_outline_rounded, tone: AppTone.warning, title: "About this guide", message: prep.disclaimer),
            Gap.xl,
            if (prep.about != null) DetailSection(title: "About the Company", child: Text(prep.about!, style: context.text.bodyLarge)),
            if (prep.recentDevelopments.isNotEmpty)
              DetailSection(
                title: "Recent Developments",
                child: CareerListGroup(
                  children: [
                    for (final post in prep.recentDevelopments)
                      CareerListRow(
                        icon: AppIcons.intelligence,
                        tone: AppTone.info,
                        title: post.headline,
                        subtitle: [
                          if (post.summary != null) post.summary!,
                          if (post.publishedAt != null) DateLabels.published(post.publishedAt!),
                        ].join(" · "),
                      ),
                  ],
                ),
              ),
            if (prep.roleRelevance != null) DetailSection(title: "Role Relevance", child: Text(prep.roleRelevance!, style: context.text.bodyLarge)),
            if (prep.likelyTopics.isNotEmpty)
              DetailSection(
                title: "Likely Topics to Prepare",
                child: Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [for (final topic in prep.likelyTopics) TagChip(label: topic, tone: AppTone.primary)],
                ),
              ),
            if (prep.openJobs.isNotEmpty)
              DetailSection(
                title: "Other Open Roles",
                child: CareerListGroup(
                  children: [
                    for (final job in prep.openJobs) CareerListRow(icon: AppIcons.job, title: job.title, subtitle: job.location),
                  ],
                ),
              ),
            DetailSection(
              title: "Before Your Interview",
              icon: Icons.checklist_rounded,
              child: progressAsync.when(
                loading: () => const LoadingSkeleton(height: 120, radius: AppRadius.card),
                error: (e, _) => Text(e.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
                data: (progress) {
                  final done = progress.checklist.where((i) => i.isDone).length;
                  return CareerCard(
                    variant: CareerCardVariant.outlined,
                    padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, AppSpacing.xs, AppSpacing.xs),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (progress.checklist.isNotEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(right: AppSpacing.sm),
                            child: CareerProgressBar(
                              value: done / progress.checklist.length,
                              tone: AppTone.success,
                              semanticLabel: "Research checklist",
                              semanticValue: "$done of ${progress.checklist.length} done",
                            ),
                          ),
                          Gap.xs,
                        ],
                        for (final item in progress.checklist)
                          CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            controlAffinity: ListTileControlAffinity.leading,
                            title: Text(
                              item.label,
                              style: context.text.bodyLarge?.copyWith(
                                decoration: item.isDone ? TextDecoration.lineThrough : null,
                                color: item.isDone ? context.colors.textSecondary : null,
                              ),
                            ),
                            value: item.isDone,
                            onChanged: (checked) async {
                              await ref.read(interviewRepositoryProvider).updateChecklistItem(
                                    key: item.key,
                                    isDone: checked ?? false,
                                    applicationId: applicationId,
                                  );
                              ref.invalidate(preparationProgressProvider);
                              ref.invalidate(interviewReadinessProvider);
                            },
                          ),
                      ],
                    ),
                  );
                },
              ),
            ),
            DetailSection(
              title: "Questions to Ask the Interviewer",
              icon: Icons.question_answer_outlined,
              child: progressAsync.when(
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
                data: (progress) => Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final q in progress.questionsToAsk)
                      Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                        child: CareerCard(
                          variant: CareerCardVariant.outlined,
                          padding: const EdgeInsets.all(AppSpacing.sm),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(q.text, style: context.text.bodyLarge),
                              Gap.xs,
                              Row(
                                children: [
                                  TagChip(label: q.category),
                                  const Spacer(),
                                  _StatusToggle(
                                    label: "Saved",
                                    selected: q.status == "saved",
                                    onTap: () async {
                                      await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
                                            id: q.id,
                                            status: q.status == "saved" ? null : "saved",
                                            applicationId: applicationId,
                                          );
                                      ref.invalidate(preparationProgressProvider);
                                    },
                                  ),
                                  Gap.xxs,
                                  _StatusToggle(
                                    label: "Planned",
                                    selected: q.status == "planned",
                                    onTap: () async {
                                      await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
                                            id: q.id,
                                            status: q.status == "planned" ? null : "planned",
                                            applicationId: applicationId,
                                          );
                                      ref.invalidate(preparationProgressProvider);
                                    },
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    Gap.xs,
                    AppOutlineButton(label: "Add your own question", icon: AppIcons.add, onPressed: () => _addCustomQuestion(context, ref)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _addCustomQuestion(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final text = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Add a question"),
        content: TextField(controller: controller, autofocus: true, decoration: const InputDecoration(hintText: "Your question")),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.of(context).pop(controller.text.trim()), child: const Text("Add")),
        ],
      ),
    );
    controller.dispose();
    if (text == null || text.isEmpty) return;
    await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
          text: text,
          category: "Role",
          status: "planned",
          isCustom: true,
          applicationId: applicationId,
        );
    ref.invalidate(preparationProgressProvider);
  }
}

class _StatusToggle extends StatelessWidget {
  const _StatusToggle({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppFilterChip(label: label, selected: selected, onSelected: (_) => onTap());
  }
}
