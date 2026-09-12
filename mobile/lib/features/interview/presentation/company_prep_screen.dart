import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
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
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(e.userMessage)),
        data: (prep) => ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(prep.companyName ?? "Company", style: Theme.of(context).textTheme.headlineSmall),
            if (prep.industry != null) Text(prep.industry!, style: const TextStyle(color: AppColors.muted)),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppColors.warning.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
              child: Text(prep.disclaimer, style: const TextStyle(fontSize: 12)),
            ),
            const SizedBox(height: 20),
            if (prep.about != null) ...[
              Text("About the Company", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(prep.about!),
              const SizedBox(height: 20),
            ],
            if (prep.recentDevelopments.isNotEmpty) ...[
              Text("Recent Developments", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              for (final post in prep.recentDevelopments)
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(post.headline),
                    subtitle: post.summary != null ? Text(post.summary!, maxLines: 2, overflow: TextOverflow.ellipsis) : null,
                    trailing: post.publishedAt != null ? Text(DateFormat.MMMd().format(post.publishedAt!), style: const TextStyle(fontSize: 11)) : null,
                  ),
                ),
              const SizedBox(height: 12),
            ],
            if (prep.roleRelevance != null) ...[
              Text("Role Relevance", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(prep.roleRelevance!),
              const SizedBox(height: 20),
            ],
            if (prep.likelyTopics.isNotEmpty) ...[
              Text("Likely Topics to Prepare", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [for (final topic in prep.likelyTopics) Chip(label: Text(topic))]),
              const SizedBox(height: 20),
            ],
            if (prep.openJobs.isNotEmpty) ...[
              Text("Other Open Roles", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              for (final job in prep.openJobs) ListTile(title: Text(job.title), subtitle: job.location != null ? Text(job.location!) : null, dense: true),
              const SizedBox(height: 12),
            ],
            const Divider(height: 32),
            Text("Before Your Interview", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            progressAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
              data: (progress) => Column(
                children: [
                  for (final item in progress.checklist)
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(item.label),
                      value: item.isDone,
                      onChanged: (checked) async {
                        await ref.read(interviewRepositoryProvider).updateChecklistItem(
                              key: item.key, isDone: checked ?? false, applicationId: applicationId,
                            );
                        ref.invalidate(preparationProgressProvider);
                        ref.invalidate(interviewReadinessProvider);
                      },
                    ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text("Questions to Ask the Interviewer", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            progressAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (progress) => Column(
                children: [
                  for (final q in progress.questionsToAsk)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(q.text),
                        subtitle: Text(q.category, style: const TextStyle(fontSize: 11)),
                        trailing: Wrap(
                          spacing: 4,
                          children: [
                            _StatusChip(
                              label: "Saved",
                              selected: q.status == "saved",
                              onTap: () async {
                                await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
                                      id: q.id, status: q.status == "saved" ? null : "saved", applicationId: applicationId,
                                    );
                                ref.invalidate(preparationProgressProvider);
                              },
                            ),
                            _StatusChip(
                              label: "Planned",
                              selected: q.status == "planned",
                              onTap: () async {
                                await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
                                      id: q.id, status: q.status == "planned" ? null : "planned", applicationId: applicationId,
                                    );
                                ref.invalidate(preparationProgressProvider);
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.add),
                    label: const Text("Add your own question"),
                    onPressed: () => _addCustomQuestion(context, ref),
                  ),
                ],
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
    if (text == null || text.isEmpty) return;
    await ref.read(interviewRepositoryProvider).updateQuestionToAsk(
          text: text, category: "Role", status: "planned", isCustom: true, applicationId: applicationId,
        );
    ref.invalidate(preparationProgressProvider);
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(label, style: const TextStyle(fontSize: 11)),
      backgroundColor: selected ? AppColors.blue.withValues(alpha: 0.15) : null,
      labelStyle: TextStyle(color: selected ? AppColors.blue : null),
      onPressed: onTap,
    );
  }
}
