import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../../aptitude/data/aptitude_models.dart";
import "../../aptitude/presentation/test_configuration_screen.dart";
import "../../applications/data/application_models.dart";
import "../../applications/presentation/application_providers.dart";
import "../../applications/presentation/stage_badge.dart";
import "../../interview/data/interview_models.dart";
import "../../interview/presentation/interview_configuration_screen.dart";
import "../data/email_tracking_models.dart";
import "email_tracking_providers.dart";

/// "Recruitment Update Detected" (spec §28) — the single screen from which a suggestion becomes a
/// real, confirmed application-stage change (or is dismissed). `Confirm Stage` is the only button
/// on this whole screen that can ever change `Application.currentStage`, and it does so purely by
/// calling the existing confirm endpoint, which itself only ever calls the Phase 5 stage service.
/// Recruitment intelligence, not an inbox: the email itself stays hidden until the user asks.
class RecruitmentEventDetailScreen extends ConsumerStatefulWidget {
  const RecruitmentEventDetailScreen({super.key, required this.eventId});

  final String eventId;

  @override
  ConsumerState<RecruitmentEventDetailScreen> createState() => _RecruitmentEventDetailScreenState();
}

class _RecruitmentEventDetailScreenState extends ConsumerState<RecruitmentEventDetailScreen> {
  bool _busy = false;
  bool _showEmailDetails = false;

  Future<void> _confirm(RecruitmentEmailEvent event) async {
    setState(() => _busy = true);
    try {
      final repo = ref.read(emailTrackingRepositoryProvider);
      final confirmed = await repo.confirmEvent(event.id);
      ref.invalidate(recruitmentEventDetailProvider(event.id));
      ref.invalidate(recruitmentEventsProvider);
      if (confirmed.matchedApplicationId != null) {
        ref.invalidate(applicationDetailProvider(confirmed.matchedApplicationId!));
      }
      final prepFlow = await repo.getPrepHint(event.id);
      if (mounted) await _showConfirmedDialog(confirmed, prepFlow);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _showConfirmedDialog(RecruitmentEmailEvent event, String? prepFlow) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: const Icon(Icons.check_circle_rounded, color: AppColors.success),
        title: const Text("Stage updated."),
        content: Text(
          prepFlow == "aptitude"
              ? "Prepare for Aptitude Test"
              : prepFlow == "interview"
                  ? "Prepare for Interview"
                  : "Your application timeline has been updated.",
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Later")),
          if (prepFlow != null)
            FilledButton(
              onPressed: () {
                Navigator.of(context).pop();
                if (prepFlow == "aptitude") {
                  context.pushReplacement(
                    "/prepare/aptitude/configure",
                    extra: AptitudeConfigureArgs(initialMode: TestMode.jobSpecific, applicationId: event.matchedApplicationId),
                  );
                } else {
                  context.pushReplacement(
                    "/prepare/interview/configure",
                    extra: InterviewConfigureArgs(initialMode: InterviewSessionMode.practice, applicationId: event.matchedApplicationId),
                  );
                }
              },
              child: Text(prepFlow == "aptitude" ? "Prepare for Aptitude Test" : "Prepare for Interview"),
            )
          else
            FilledButton(onPressed: () => context.pop(), child: const Text("Done")),
        ],
      ),
    );
  }

  Future<void> _ignore(RecruitmentEmailEvent event) async {
    setState(() => _busy = true);
    try {
      await ref.read(emailTrackingRepositoryProvider).ignoreEvent(event.id);
      ref.invalidate(recruitmentEventDetailProvider(event.id));
      ref.invalidate(recruitmentEventsProvider);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickApplication(RecruitmentEmailEvent event) async {
    final chosen = await showModalBottomSheet<String?>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => _AmbiguousApplicationPicker(candidateIds: event.candidateApplicationIds),
    );
    if (chosen == null) return;
    setState(() => _busy = true);
    try {
      await ref.read(emailTrackingRepositoryProvider).assignApplication(event.id, chosen);
      ref.invalidate(recruitmentEventDetailProvider(event.id));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventAsync = ref.watch(recruitmentEventDetailProvider(widget.eventId));
    return Scaffold(
      appBar: AppBar(title: const Text("Recruitment Update Detected")),
      body: eventAsync.when(
        loading: () => const SkeletonList(itemCount: 2),
        error: (e, _) => ErrorState(
          title: "We couldn't load this update",
          message: e.userMessage,
          onRetry: () => ref.invalidate(recruitmentEventDetailProvider(widget.eventId)),
        ),
        data: (event) => _buildBody(context, event),
      ),
    );
  }

  Widget _buildBody(BuildContext context, RecruitmentEmailEvent event) {
    final applicationAsync = event.matchedApplicationId != null ? ref.watch(applicationDetailProvider(event.matchedApplicationId!)) : null;
    final confidenceTone = switch (event.confidenceLabel) {
      "HIGH" => AppTone.success,
      "MEDIUM" => AppTone.warning,
      _ => AppTone.neutral,
    };

    return ListView(
      padding: AppSpacing.page,
      children: [
        if (applicationAsync != null)
          applicationAsync.when(
            loading: () => const SkeletonCard(),
            error: (_, __) => const SizedBox.shrink(),
            data: (application) => CareerCard(
              child: Row(
                children: [
                  NetworkImageWithFallback(url: null, fallbackText: application.companyName, size: 48),
                  Gap.sm,
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Matched application", style: context.text.labelSmall),
                        Text(application.companyName, style: context.text.titleMedium),
                        Text(application.roleTitle, style: context.text.bodyMedium),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (event.status == RecruitmentEventStatus.ambiguous) ...[
          Gap.sm,
          const InsightCard(
            icon: Icons.help_outline_rounded,
            tone: AppTone.warning,
            title: "More than one possible match",
            message: "CareerOS found more than one of your applications this could belong to — pick the right one below.",
          ),
        ],
        Gap.sm,
        CareerCard(
          variant: CareerCardVariant.feature,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (event.detectedStage != null) ...[
                Text("Possible new stage", style: context.text.labelMedium),
                Gap.xs,
                Row(
                  children: [
                    IconTile(icon: stageIcon(event.detectedStage!), tone: stageTone(event.detectedStage!), size: 40),
                    Gap.sm,
                    Expanded(child: Text(event.detectedStage!.label, style: context.text.titleLarge)),
                  ],
                ),
                Gap.md,
              ],
              Wrap(
                spacing: AppSpacing.xs,
                runSpacing: AppSpacing.xs,
                children: [
                  if (event.confidenceLabel != null)
                    StatusChip(label: "Confidence: ${_confidenceLabel(event.confidenceLabel!)}", tone: confidenceTone, icon: Icons.speed_rounded),
                  TagChip(label: "Email received ${DateLabels.shortDate(event.receivedAt)}", icon: AppIcons.email),
                ],
              ),
              Gap.sm,
              AppTextButton(
                label: "View Email Details",
                icon: _showEmailDetails ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                onPressed: () => setState(() => _showEmailDetails = !_showEmailDetails),
              ),
              if (_showEmailDetails) _EmailDetailsCard(event: event),
            ],
          ),
        ),
        Gap.md,
        Row(
          children: [
            const Icon(Icons.verified_user_outlined, size: 16, color: AppColors.success),
            Gap.xs,
            Expanded(child: Text("Nothing changes on your application until you confirm.", style: context.text.bodySmall)),
          ],
        ),
        Gap.lg,
        if (event.status == RecruitmentEventStatus.ambiguous)
          PrimaryButton(label: "Which Application Does This Belong To?", onPressed: _busy ? null : () => _pickApplication(event))
        else if (event.status == RecruitmentEventStatus.suggested) ...[
          PrimaryButton(label: "Confirm Stage", icon: AppIcons.check, isLoading: _busy, onPressed: () => _confirm(event)),
          Gap.sm,
          AppOutlineButton(label: "Wrong Application", onPressed: _busy ? null : () => _pickApplication(event)),
          Gap.xs,
          Center(child: TextButton(onPressed: _busy ? null : () => _ignore(event), child: const Text("Ignore"))),
        ] else if (event.status == RecruitmentEventStatus.confirmed)
          const _StatusBanner(text: "Confirmed", tone: AppTone.success)
        else if (event.status == RecruitmentEventStatus.ignored)
          const _StatusBanner(text: "Ignored", tone: AppTone.neutral)
        else
          const _StatusBanner(text: "No application matched", tone: AppTone.neutral),
      ],
    );
  }

  String _confidenceLabel(String label) => switch (label) {
        "HIGH" => "High",
        "MEDIUM" => "Medium",
        _ => "Low",
      };
}

class _EmailDetailsCard extends StatelessWidget {
  const _EmailDetailsCard({required this.event});

  final RecruitmentEmailEvent event;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: AppSpacing.xs),
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(color: context.colors.surfaceMuted, borderRadius: AppRadius.mdAll),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _EmailField(label: "From", value: event.senderName != null ? "${event.senderName} <${event.senderEmail}>" : event.senderEmail),
          _EmailField(label: "Subject", value: event.subject),
          _EmailField(label: "Date", value: DateLabels.dateTime(event.receivedAt)),
          if (event.evidenceExcerpt != null) _EmailField(label: "Excerpt", value: event.evidenceExcerpt!),
          Gap.xs,
          Text("Detected because:", style: context.text.labelMedium),
          for (final reason in event.evidence) Text("• $reason", style: context.text.bodySmall),
        ],
      ),
    );
  }
}

class _EmailField extends StatelessWidget {
  const _EmailField({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text.rich(
        TextSpan(
          style: context.text.bodyMedium?.copyWith(color: context.colors.textPrimary),
          children: [
            TextSpan(text: "$label: ", style: const TextStyle(fontWeight: FontWeight.w600)),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.text, required this.tone});

  final String text;
  final AppTone tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(color: tone.tint(context), borderRadius: AppRadius.cardAll),
      child: Text(text, textAlign: TextAlign.center, style: context.text.titleSmall?.copyWith(color: tone.onTint(context))),
    );
  }
}

/// Spec §25 — "Which application does this email belong to?" Never guesses: only the candidates
/// the matcher itself flagged as plausible are offered, plus an explicit "None of These".
class _AmbiguousApplicationPicker extends ConsumerWidget {
  const _AmbiguousApplicationPicker({required this.candidateIds});

  final List<String> candidateIds;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Which application does this email belong to?", style: context.text.titleLarge),
            Gap.sm,
            for (final id in candidateIds) _CandidateTile(applicationId: id),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.close_rounded),
              title: const Text("None of These"),
              onTap: () => Navigator.of(context).pop(null),
            ),
          ],
        ),
      ),
    );
  }
}

class _CandidateTile extends ConsumerWidget {
  const _CandidateTile({required this.applicationId});

  final String applicationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applicationAsync = ref.watch(applicationDetailProvider(applicationId));
    return applicationAsync.when(
      loading: () => const ListTile(title: LoadingSkeleton(height: 16)),
      error: (_, __) => const SizedBox.shrink(),
      data: (Application application) => ListTile(
        leading: NetworkImageWithFallback(url: null, fallbackText: application.companyName, size: 40),
        title: Text("${application.companyName} — ${application.roleTitle}"),
        trailing: StageBadge(stage: application.currentStage, dense: true),
        onTap: () => Navigator.of(context).pop(applicationId),
      ),
    );
  }
}
