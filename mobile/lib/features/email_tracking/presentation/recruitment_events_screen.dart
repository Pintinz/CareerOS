import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/email_tracking_models.dart";
import "email_tracking_providers.dart";

/// The "Recruitment Update Detected" list (spec §28/§31) — every event the user hasn't reviewed
/// yet, plus recently-reviewed ones for context. Never shows raw subject/body on its own — see
/// [RecruitmentEventDetailScreen] for the explainability detail (spec §29).
class RecruitmentEventsScreen extends ConsumerWidget {
  const RecruitmentEventsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(recruitmentEventsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text("Application Updates")),
      body: eventsAsync.when(
        loading: () => const SkeletonList(),
        error: (e, _) => ErrorState(
          title: "We couldn't load your updates",
          message: e.userMessage,
          onRetry: () => ref.invalidate(recruitmentEventsProvider),
        ),
        data: (events) {
          if (events.isEmpty) {
            return const EmptyState(
              icon: AppIcons.email,
              title: "No recruitment updates yet",
              message: "When Smart Application Tracking spots an assessment invite, interview or offer, it appears here for you to review.",
            );
          }
          final needsReview = events.where((e) => e.needsReview).toList();
          final reviewed = events.where((e) => !e.needsReview).toList();
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(recruitmentEventsProvider),
            child: ListView(
              padding: AppSpacing.page,
              children: [
                if (needsReview.isNotEmpty) ...[
                  SectionHeader(title: "Needs review", subtitle: "${needsReview.length} waiting for your confirmation"),
                  _EventGroup(events: needsReview),
                ],
                if (reviewed.isNotEmpty) ...[
                  if (needsReview.isNotEmpty) Gap.section,
                  const SectionHeader(title: "Recently reviewed"),
                  _EventGroup(events: reviewed),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _EventGroup extends StatelessWidget {
  const _EventGroup({required this.events});

  final List<RecruitmentEmailEvent> events;

  @override
  Widget build(BuildContext context) {
    return CareerListGroup(
      children: [
        for (final event in events)
          CareerListRow(
            icon: event.needsReview ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined,
            tone: event.needsReview ? AppTone.primary : AppTone.neutral,
            title: event.detectedStage != null ? "Possible ${event.detectedStage!.label} update" : "Recruitment email",
            subtitle: "${event.senderDomain} · ${DateFormat.yMMMd().format(event.receivedAt)} · ${_statusLabel(event.status)}",
            trailing: event.confidenceLabel != null ? _ConfidenceBadge(label: event.confidenceLabel!) : null,
            onTap: () => context.push("/settings/tracking/events/${event.id}"),
          ),
      ],
    );
  }

  String _statusLabel(RecruitmentEventStatus status) => switch (status) {
        RecruitmentEventStatus.suggested => "Needs review",
        RecruitmentEventStatus.ambiguous => "Which application?",
        RecruitmentEventStatus.confirmed => "Confirmed",
        RecruitmentEventStatus.ignored => "Ignored",
        RecruitmentEventStatus.unmatched => "No application matched",
        RecruitmentEventStatus.detected => "Detected",
      };
}

class _ConfidenceBadge extends StatelessWidget {
  const _ConfidenceBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final tone = switch (label) {
      "HIGH" => AppTone.success,
      "MEDIUM" => AppTone.warning,
      _ => AppTone.neutral,
    };
    final text = switch (label) {
      "HIGH" => "High",
      "MEDIUM" => "Medium",
      _ => "Low",
    };
    return StatusChip(label: text, tone: tone, dense: true);
  }
}
