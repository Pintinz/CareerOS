import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
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
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(e.userMessage, style: const TextStyle(color: AppColors.danger))),
        data: (events) {
          if (events.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text("No recruitment updates detected yet.", style: TextStyle(color: AppColors.muted)),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(recruitmentEventsProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: events.length,
              separatorBuilder: (context, index) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final event = events[index];
                return _EventCard(event: event, onTap: () => context.push("/settings/tracking/events/${event.id}"));
              },
            ),
          );
        },
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event, required this.onTap});

  final RecruitmentEmailEvent event;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final needsReview = event.needsReview;
    return Card(
      child: ListTile(
        onTap: onTap,
        leading: Icon(
          needsReview ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined,
          color: needsReview ? AppColors.blue : AppColors.muted,
        ),
        title: Text(
          event.detectedStage != null ? "Possible ${event.detectedStage!.label} update" : "Recruitment email",
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          "${event.senderDomain} · ${DateFormat.yMMMd().format(event.receivedAt)} · ${_statusLabel(event.status)}",
          style: const TextStyle(fontSize: 12),
        ),
        trailing: event.confidenceLabel != null ? _ConfidenceBadge(label: event.confidenceLabel!) : null,
      ),
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
    final color = switch (label) {
      "HIGH" => AppColors.success,
      "MEDIUM" => AppColors.warning,
      _ => AppColors.muted,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
      child: Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w700)),
    );
  }
}
