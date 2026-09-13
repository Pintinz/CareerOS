import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../../aptitude/data/aptitude_models.dart";
import "../../aptitude/presentation/test_configuration_screen.dart";
import "../../email_tracking/data/email_tracking_models.dart";
import "../../email_tracking/presentation/email_tracking_providers.dart";
import "../../interview/data/interview_models.dart";
import "../../interview/presentation/interview_configuration_screen.dart";
import "../../interview/presentation/interview_providers.dart";
import "../data/application_models.dart";
import "application_providers.dart";
import "stage_badge.dart";
import "update_stage_sheet.dart";

class ApplicationDetailScreen extends ConsumerStatefulWidget {
  const ApplicationDetailScreen({super.key, required this.applicationId});

  final String applicationId;

  @override
  ConsumerState<ApplicationDetailScreen> createState() => _ApplicationDetailScreenState();
}

class _ApplicationDetailScreenState extends ConsumerState<ApplicationDetailScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 4, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _updateStage(Application application) async {
    final result = await showUpdateStageSheet(context, application.currentStage);
    if (result == null) return;
    final (stage, note) = result;
    try {
      await ref.read(applicationRepositoryProvider).updateStage(application.id, stage, note: note);
      ref.invalidate(applicationDetailProvider(application.id));
      ref.read(applicationListProvider.notifier).refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
      }
    }
  }

  Future<void> _deleteApplication(Application application) async {
    final confirmed = await showCareerDialog(
      context: context,
      title: "Stop tracking this application?",
      message: "This removes it and its history. This can't be undone.",
      confirmLabel: "Delete",
      destructive: true,
    );
    if (!confirmed) return;
    await ref.read(applicationRepositoryProvider).delete(application.id);
    ref.read(applicationListProvider.notifier).refresh();
    if (mounted) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(applicationDetailProvider(widget.applicationId));

    return detailAsync.when(
      loading: () => const DetailSkeleton(),
      error: (error, _) => DetailError(
        title: "We couldn't load this application",
        message: error.userMessage,
        onRetry: () => ref.invalidate(applicationDetailProvider(widget.applicationId)),
      ),
      data: (application) => DetailScaffold(
        showBanner: false,
        title: "Application",
        tabController: _tabController,
        actions: [
          IconButton(
            tooltip: "Stop tracking",
            icon: const Icon(AppIcons.delete),
            onPressed: () => _deleteApplication(application),
          ),
        ],
        header: _ApplicationHeader(application: application),
        tabs: const ["Details", "Timeline", "Notes", "Emails"],
        tabViews: [
          _DetailsTab(application: application),
          _TimelineTab(application: application),
          _NotesTab(application: application),
          _EmailsTab(applicationId: application.id),
        ],
        bottomBar: BottomActionBar(
          secondary: application.jobUrl != null
              ? AppOutlineButton(
                  expand: false,
                  label: "View Job",
                  icon: AppIcons.external,
                  onPressed: () => openExternalUrl(context, application.jobUrl),
                )
              : null,
          primary: PrimaryButton(label: "Update Stage", icon: Icons.swap_vert_rounded, onPressed: () => _updateStage(application)),
        ),
      ),
    );
  }
}

bool _isInterviewStage(ApplicationStage stage) => const {
      ApplicationStage.interview,
      ApplicationStage.finalInterview,
      ApplicationStage.recruiterScreen,
      ApplicationStage.assessmentCentre,
    }.contains(stage);

/// Spec §38: stage-aware preparation hints. Aptitude (Phase 6) and Interview (Phase 7) get real
/// cards; only stages with no dedicated preparation flow fall back to plain text.
String? _stagePrepHint(ApplicationStage stage) => switch (stage) {
      ApplicationStage.medical => "Keep any requested medical/documentation paperwork ready for this stage.",
      _ => null,
    };

class _ApplicationHeader extends StatelessWidget {
  const _ApplicationHeader({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    final hint = _stagePrepHint(application.currentStage);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            NetworkImageWithFallback(url: null, fallbackText: application.companyName, size: 56, tone: stageTone(application.currentStage)),
            Gap.md,
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(application.roleTitle, style: context.text.headlineSmall),
                  Text(application.companyName, style: context.text.bodyLarge?.copyWith(color: context.colors.textSecondary)),
                ],
              ),
            ),
          ],
        ),
        Gap.sm,
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.xs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            StageBadge(stage: application.currentStage),
            Text("Updated ${DateLabels.published(application.updatedAt).toLowerCase()}", style: context.text.bodySmall),
          ],
        ),
        if (application.currentStage == ApplicationStage.aptitudeTest) ...[
          Gap.md,
          _AptitudePrepCard(application: application),
        ] else if (_isInterviewStage(application.currentStage)) ...[
          Gap.md,
          _InterviewPrepCard(application: application),
        ] else if (hint != null) ...[
          Gap.md,
          InsightCard(icon: Icons.info_outline_rounded, tone: AppTone.warning, title: "Stage tip", message: hint),
        ],
      ],
    );
  }
}

class _AptitudePrepCard extends StatelessWidget {
  const _AptitudePrepCard({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      variant: CareerCardVariant.outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const IconTile(icon: AppIcons.aptitude, tone: AppTone.purple, size: 36),
              Gap.sm,
              Expanded(child: Text("Upcoming: Aptitude Test", style: context.text.titleSmall)),
            ],
          ),
          Gap.xs,
          Text(
            "Practice with questions tailored to this role. Practicing here never changes this application's stage — "
            "update it yourself once you've taken the employer's real assessment.",
            style: context.text.bodySmall,
          ),
          Gap.sm,
          PrimaryButton(
            label: "Prepare for Aptitude Test",
            onPressed: () => context.push(
              "/prepare/aptitude/configure",
              extra: AptitudeConfigureArgs(initialMode: TestMode.jobSpecific, applicationId: application.id),
            ),
          ),
        ],
      ),
    );
  }
}

/// Real "Interview Preparation" card (spec §29) for interview-related stages: readiness, questions
/// practiced, STAR stories ready — preparing here never mutates the application's real stage.
class _InterviewPrepCard extends ConsumerWidget {
  const _InterviewPrepCard({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readiness = ref.watch(interviewReadinessProvider(application.id)).valueOrNull;
    final analytics = ref.watch(interviewAnalyticsProvider).valueOrNull;
    final readinessLabel = readiness == null ? null : (readiness.insufficientData || readiness.overall == null ? "N/A" : "${readiness.overall!.round()}%");

    return CareerCard(
      variant: CareerCardVariant.outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const IconTile(icon: AppIcons.interview, tone: AppTone.warning, size: 36),
              Gap.sm,
              Expanded(child: Text("Interview Preparation", style: context.text.titleSmall)),
            ],
          ),
          Gap.xs,
          Text(
            "Practicing here never changes this application's stage — update it yourself once you've completed the "
            "employer's real interview.",
            style: context.text.bodySmall,
          ),
          Gap.md,
          Row(
            children: [
              Expanded(child: MetricTile(label: "Readiness", value: readinessLabel)),
              Expanded(child: MetricTile(label: "Questions", value: analytics?.questionsPracticed.toString())),
              Expanded(child: MetricTile(label: "STAR Ready", value: analytics?.starStoriesReady.toString())),
            ],
          ),
          Gap.md,
          Row(
            children: [
              if (application.jobId != null) ...[
                Expanded(
                  child: AppOutlineButton(
                    label: "Company Research",
                    onPressed: () => context.push("/prepare/interview/company-prep/${application.id}"),
                  ),
                ),
                Gap.xs,
              ],
              Expanded(
                flex: 2,
                child: PrimaryButton(
                  label: "Continue Preparation",
                  onPressed: () => context.push(
                    "/prepare/interview/configure",
                    extra: InterviewConfigureArgs(initialMode: InterviewSessionMode.practice, applicationId: application.id),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DetailsTab extends StatelessWidget {
  const _DetailsTab({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    final dateTime = DateFormat.yMMMd().add_jm();
    final rows = <(IconData, String, String?)>[
      (AppIcons.location, "Location", application.location),
      (Icons.send_rounded, "Applied", application.appliedDate != null ? DateLabels.shortDate(application.appliedDate!) : null),
      (AppIcons.deadline, "Deadline", application.deadline != null ? DateLabels.shortDate(application.deadline!) : null),
      (AppIcons.interview, "Interview", application.interviewDate != null ? dateTime.format(application.interviewDate!) : null),
      (AppIcons.aptitude, "Assessment", application.assessmentDate != null ? dateTime.format(application.assessmentDate!) : null),
      (Icons.payments_outlined, "Salary", application.salary),
      (AppIcons.profile, "Contact", application.contactName),
      (Icons.alternate_email_rounded, "Contact email", application.contactEmail),
    ].where((e) => e.$3 != null).toList();

    if (rows.isEmpty && application.coverLetterText == null) {
      return const EmptyState(
        compact: true,
        icon: Icons.edit_note_rounded,
        title: "No additional details yet",
        message: "Dates, contacts and salary you record for this application will appear here.",
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (rows.isNotEmpty)
          CareerCard(
            variant: CareerCardVariant.outlined,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
            child: Column(children: [for (final row in rows) FactRow(icon: row.$1, label: row.$2, value: row.$3!)]),
          ),
        if (application.coverLetterText != null) ...[
          Gap.xl,
          DetailSection(title: "Cover Letter", child: Text(application.coverLetterText!, style: context.text.bodyLarge)),
        ],
      ],
    );
  }
}

/// Stages in the order a typical application moves through them — used only to suggest the *next
/// expected* step, never to rewrite or reorder the recorded history.
const _typicalProgression = [
  ApplicationStage.saved,
  ApplicationStage.applied,
  ApplicationStage.applicationReceived,
  ApplicationStage.underReview,
  ApplicationStage.shortlisted,
  ApplicationStage.aptitudeTest,
  ApplicationStage.recruiterScreen,
  ApplicationStage.interview,
  ApplicationStage.finalInterview,
  ApplicationStage.offer,
  ApplicationStage.hired,
];

class _TimelineTab extends StatelessWidget {
  const _TimelineTab({required this.application});

  final Application application;

  ApplicationStage? get _nextExpected {
    final current = application.currentStage;
    if (current.isTerminal) return null;
    final index = _typicalProgression.indexOf(current);
    if (index == -1 || index == _typicalProgression.length - 1) return null;
    return _typicalProgression[index + 1];
  }

  @override
  Widget build(BuildContext context) {
    final events = application.timeline; // oldest first, exactly as recorded
    if (events.isEmpty) {
      return const EmptyState(
        compact: true,
        icon: AppIcons.application,
        title: "No history yet",
        message: "Each stage update you make is recorded here as a timeline.",
      );
    }
    final next = _nextExpected;
    final dateTime = DateFormat.yMMMd().add_jm();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < events.length; i++)
          _TimelineEntry(
            marker: i == events.length - 1 ? _Marker.current : _Marker.done,
            title: events[i].stage.label,
            subtitle: dateTime.format(events[i].occurredAt),
            note: events[i].note,
            tone: stageTone(events[i].stage),
            showRail: i < events.length - 1 || next != null,
          ),
        if (next != null)
          _TimelineEntry(
            marker: _Marker.future,
            title: next.label,
            subtitle: "Typical next step — update the stage when it happens",
            tone: AppTone.neutral,
            showRail: false,
          ),
      ],
    );
  }
}

enum _Marker { done, current, future }

class _TimelineEntry extends StatelessWidget {
  const _TimelineEntry({
    required this.marker,
    required this.title,
    required this.subtitle,
    required this.tone,
    required this.showRail,
    this.note,
  });

  final _Marker marker;
  final String title;
  final String subtitle;
  final String? note;
  final AppTone tone;
  final bool showRail;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final markerWidget = switch (marker) {
      _Marker.done => const Icon(Icons.check_circle_rounded, size: 22, color: AppColors.success),
      _Marker.current => Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(shape: BoxShape.circle, color: tone.tint(context), border: Border.all(color: tone.color(context), width: 2)),
          alignment: Alignment.center,
          child: Container(width: 8, height: 8, decoration: BoxDecoration(color: tone.color(context), shape: BoxShape.circle)),
        ),
      _Marker.future => Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: colors.border, width: 2)),
        ),
    };

    return Semantics(
      label: "${switch (marker) { _Marker.done => "Completed", _Marker.current => "Current stage", _Marker.future => "Expected next" }}: $title",
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              width: 28,
              child: Column(
                children: [
                  markerWidget,
                  if (showRail) Expanded(child: Container(width: 2, margin: const EdgeInsets.symmetric(vertical: 4), color: colors.border)),
                ],
              ),
            ),
            Gap.sm,
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: context.text.titleSmall?.copyWith(color: marker == _Marker.future ? colors.textSecondary : null),
                    ),
                    Text(subtitle, style: context.text.bodySmall),
                    if (note != null && note!.isNotEmpty) ...[
                      Gap.xs,
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(AppSpacing.sm),
                        decoration: BoxDecoration(color: colors.surfaceMuted, borderRadius: AppRadius.mdAll),
                        child: Text(note!, style: context.text.bodyMedium?.copyWith(color: colors.textPrimary)),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NotesTab extends ConsumerStatefulWidget {
  const _NotesTab({required this.application});

  final Application application;

  @override
  ConsumerState<_NotesTab> createState() => _NotesTabState();
}

class _NotesTabState extends ConsumerState<_NotesTab> {
  final _noteController = TextEditingController();
  bool _adding = false;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _addNote() async {
    final text = _noteController.text.trim();
    if (text.isEmpty) return;
    setState(() => _adding = true);
    try {
      await ref.read(applicationRepositoryProvider).addNote(widget.application.id, text);
      _noteController.clear();
      ref.invalidate(applicationDetailProvider(widget.application.id));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    } finally {
      if (mounted) setState(() => _adding = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final notes = widget.application.notes;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _noteController,
          minLines: 1,
          maxLines: 4,
          textInputAction: TextInputAction.newline,
          decoration: InputDecoration(
            hintText: "Add a note — who you spoke to, what's next…",
            suffixIcon: IconButton(
              tooltip: "Save note",
              onPressed: _adding ? null : _addNote,
              icon: _adding
                  ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : Icon(Icons.send_rounded, color: context.colors.primary),
            ),
          ),
        ),
        Gap.lg,
        if (notes.isEmpty)
          const EmptyState(
            compact: true,
            icon: Icons.sticky_note_2_outlined,
            title: "No notes yet",
            message: "Keep interview feedback, contacts and follow-ups together with this application.",
          )
        else
          for (final note in notes)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: CareerCard(
                variant: CareerCardVariant.outlined,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(note.text, style: context.text.bodyLarge),
                    Gap.xs,
                    Text(DateFormat.yMMMd().add_jm().format(note.createdAt), style: context.text.bodySmall),
                  ],
                ),
              ),
            ),
      ],
    );
  }
}

/// Spec §32 — recruitment-email events matched to *this* application only, never every raw
/// mailbox message. Tapping one goes to the same confirmation screen as the dashboard/settings
/// list — there is only one place a stage can actually be confirmed from.
class _EmailsTab extends ConsumerWidget {
  const _EmailsTab({required this.applicationId});

  final String applicationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(applicationRecruitmentEventsProvider(applicationId));
    return eventsAsync.when(
      loading: () => const Column(children: [SkeletonCard()]),
      error: (e, _) => ErrorState(
        compact: true,
        message: e.userMessage,
        onRetry: () => ref.invalidate(applicationRecruitmentEventsProvider(applicationId)),
      ),
      data: (events) {
        if (events.isEmpty) {
          return const EmptyState(
            compact: true,
            icon: AppIcons.email,
            title: "No recruitment emails matched",
            message: "When Smart Application Tracking detects an email about this application, it appears here for review.",
          );
        }
        return CareerListGroup(
          children: [
            for (final event in events)
              CareerListRow(
                icon: AppIcons.email,
                tone: _statusTone(event.status),
                title: event.detectedStage != null ? "${event.detectedStage!.label} update" : "Recruitment email",
                subtitle: [
                  DateLabels.shortDate(event.receivedAt),
                  if (event.confidenceLabel != null) event.confidenceLabel!,
                  _statusLabel(event.status),
                ].join(" · "),
                onTap: () => context.push("/settings/tracking/events/${event.id}"),
              ),
          ],
        );
      },
    );
  }

  String _statusLabel(RecruitmentEventStatus status) => switch (status) {
        RecruitmentEventStatus.confirmed => "Confirmed",
        RecruitmentEventStatus.ignored => "Ignored",
        RecruitmentEventStatus.ambiguous => "Needs your input",
        RecruitmentEventStatus.suggested => "Needs review",
        _ => "Detected",
      };

  AppTone _statusTone(RecruitmentEventStatus status) => switch (status) {
        RecruitmentEventStatus.confirmed => AppTone.success,
        RecruitmentEventStatus.ignored => AppTone.neutral,
        RecruitmentEventStatus.ambiguous || RecruitmentEventStatus.suggested => AppTone.warning,
        _ => AppTone.primary,
      };
}
