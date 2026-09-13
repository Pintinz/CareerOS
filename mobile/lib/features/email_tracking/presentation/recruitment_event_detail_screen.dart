import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "../../aptitude/data/aptitude_models.dart";
import "../../aptitude/presentation/test_configuration_screen.dart";
import "../../applications/data/application_models.dart";
import "../../applications/presentation/application_providers.dart";
import "../../interview/data/interview_models.dart";
import "../../interview/presentation/interview_configuration_screen.dart";
import "../data/email_tracking_models.dart";
import "email_tracking_providers.dart";

/// "Recruitment Update Detected" (spec §28) — the single screen from which a suggestion becomes a
/// real, confirmed application-stage change (or is dismissed). `Confirm Stage` is the only button
/// on this whole screen that can ever change `Application.currentStage`, and it does so purely by
/// calling the existing confirm endpoint, which itself only ever calls the Phase 5 stage service.
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
        title: const Text("Stage updated."),
        content: Text(prepFlow == "aptitude" ? "Prepare for Aptitude Test" : prepFlow == "interview" ? "Prepare for Interview" : "Your application timeline has been updated."),
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
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(e.userMessage, style: const TextStyle(color: AppColors.danger))),
        data: (event) => _buildBody(context, event),
      ),
    );
  }

  Widget _buildBody(BuildContext context, RecruitmentEmailEvent event) {
    final applicationAsync = event.matchedApplicationId != null
        ? ref.watch(applicationDetailProvider(event.matchedApplicationId!))
        : null;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (applicationAsync != null)
            applicationAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (application) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(application.companyName, style: Theme.of(context).textTheme.headlineSmall),
                  Text(application.roleTitle, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          if (event.status == RecruitmentEventStatus.ambiguous)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(color: AppColors.warning.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
              child: const Text(
                "CareerOS found more than one of your applications this could belong to — pick the right one below.",
                style: TextStyle(fontSize: 13),
              ),
            ),
          if (event.detectedStage != null) ...[
            const Text("Possible new stage", style: TextStyle(color: AppColors.muted, fontSize: 12)),
            const SizedBox(height: 4),
            Text(event.detectedStage!.label.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
            const SizedBox(height: 8),
          ],
          if (event.confidenceLabel != null) ...[
            Text("Confidence: ${_confidenceLabel(event.confidenceLabel!)}", style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 16),
          ],
          Text(
            "Detected from:\nRecruitment email received ${DateFormat.yMMMd().format(event.receivedAt)}",
            style: const TextStyle(color: AppColors.muted),
          ),
          const SizedBox(height: 20),
          TextButton.icon(
            onPressed: () => setState(() => _showEmailDetails = !_showEmailDetails),
            icon: Icon(_showEmailDetails ? Icons.visibility_off_outlined : Icons.visibility_outlined),
            label: const Text("View Email Details"),
          ),
          if (_showEmailDetails) _EmailDetailsCard(event: event),
          const SizedBox(height: 28),
          if (event.status == RecruitmentEventStatus.ambiguous)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(onPressed: _busy ? null : () => _pickApplication(event), child: const Text("Which Application Does This Belong To?")),
            )
          else if (event.status == RecruitmentEventStatus.suggested) ...[
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(onPressed: _busy ? null : () => _confirm(event), child: const Text("Confirm Stage")),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(onPressed: _busy ? null : () => _pickApplication(event), child: const Text("Wrong Application")),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton(onPressed: _busy ? null : () => _ignore(event), child: const Text("Ignore")),
            ),
          ] else if (event.status == RecruitmentEventStatus.confirmed)
            const _StatusBanner(text: "Confirmed", color: AppColors.success)
          else if (event.status == RecruitmentEventStatus.ignored)
            const _StatusBanner(text: "Ignored", color: AppColors.muted)
          else
            const _StatusBanner(text: "No application matched", color: AppColors.muted),
        ],
      ),
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
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _EmailField(label: "From", value: event.senderName != null ? "${event.senderName} <${event.senderEmail}>" : event.senderEmail),
          _EmailField(label: "Subject", value: event.subject),
          _EmailField(label: "Date", value: DateFormat.yMMMd().add_jm().format(event.receivedAt)),
          if (event.evidenceExcerpt != null) _EmailField(label: "Excerpt", value: event.evidenceExcerpt!),
          const SizedBox(height: 8),
          const Text("Detected because:", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
          for (final reason in event.evidence) Text("• $reason", style: const TextStyle(fontSize: 12)),
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
          style: DefaultTextStyle.of(context).style.copyWith(fontSize: 13),
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
  const _StatusBanner({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
      child: Text(text, textAlign: TextAlign.center, style: TextStyle(color: color, fontWeight: FontWeight.w600)),
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
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Which application does this email belong to?", style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            for (final id in candidateIds) _CandidateTile(applicationId: id),
            const Divider(),
            ListTile(
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
      loading: () => const ListTile(title: Text("Loading...")),
      error: (_, __) => const SizedBox.shrink(),
      data: (Application application) => ListTile(
        title: Text("${application.companyName} — ${application.roleTitle}"),
        onTap: () => Navigator.of(context).pop(applicationId),
      ),
    );
  }
}
