import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../theme/app_colors.dart";
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
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

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
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Stop tracking this application?"),
        content: const Text("This removes it and its history. This can't be undone."),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Cancel")),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text("Delete", style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await ref.read(applicationRepositoryProvider).delete(application.id);
    ref.read(applicationListProvider.notifier).refresh();
    if (mounted) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(applicationDetailProvider(widget.applicationId));

    return Scaffold(
      appBar: AppBar(
        title: const Text("Application"),
        actions: [
          detailAsync.maybeWhen(
            data: (application) => IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: () => _deleteApplication(application),
            ),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
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
                  onPressed: () => ref.invalidate(applicationDetailProvider(widget.applicationId)),
                  child: const Text("Retry"),
                ),
              ],
            ),
          ),
        ),
        data: (application) => Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(application.roleTitle, style: Theme.of(context).textTheme.headlineMedium),
                        Text(application.companyName, style: Theme.of(context).textTheme.titleLarge),
                      ],
                    ),
                  ),
                  StageBadge(stage: application.currentStage),
                ],
              ),
            ),
            if (application.currentStage == ApplicationStage.aptitudeTest)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.blue.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.fact_check_outlined, size: 18, color: AppColors.blue),
                          SizedBox(width: 8),
                          Text("Upcoming: Aptitude Test", style: TextStyle(fontWeight: FontWeight.w600)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        "Practice with questions tailored to this role. Practicing here never changes this "
                        "application's stage — update it yourself once you've taken the employer's real assessment.",
                        style: TextStyle(fontSize: 12, color: AppColors.muted),
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: () => context.push(
                            "/prepare/aptitude/configure",
                            extra: AptitudeConfigureArgs(
                              initialMode: TestMode.jobSpecific,
                              applicationId: application.id,
                            ),
                          ),
                          child: const Text("Prepare for Aptitude Test"),
                        ),
                      ),
                    ],
                  ),
                ),
              )
            else if (_isInterviewStage(application.currentStage))
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                child: _InterviewPrepCard(application: application),
              )
            else if (_stagePrepHint(application.currentStage) != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline, size: 18, color: AppColors.warning),
                      const SizedBox(width: 8),
                      Expanded(child: Text(_stagePrepHint(application.currentStage)!, style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),
            TabBar(
              controller: _tabController,
              labelColor: AppColors.blue,
              unselectedLabelColor: AppColors.muted,
              indicatorColor: AppColors.blue,
              tabs: const [Tab(text: "Details"), Tab(text: "Timeline"), Tab(text: "Notes"), Tab(text: "Emails")],
            ),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _DetailsTab(application: application),
                  _TimelineTab(application: application),
                  _NotesTab(application: application),
                  _EmailsTab(applicationId: application.id),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(color: AppColors.card, border: Border(top: BorderSide(color: Color(0x1A000000)))),
              child: SafeArea(
                top: false,
                child: Row(
                  children: [
                    if (application.jobUrl != null) ...[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => openExternalUrl(context, application.jobUrl),
                          child: const Text("View Job"),
                        ),
                      ),
                      const SizedBox(width: 12),
                    ],
                    Expanded(
                      flex: 2,
                      child: ElevatedButton(
                        onPressed: () => _updateStage(application),
                        child: const Text("Update Stage"),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  bool _isInterviewStage(ApplicationStage stage) => const {
        ApplicationStage.interview,
        ApplicationStage.finalInterview,
        ApplicationStage.recruiterScreen,
        ApplicationStage.assessmentCentre,
      }.contains(stage);

  /// Spec §38: stage-aware preparation hints. Aptitude (Phase 6) and Interview (Phase 7) now get
  /// real cards above; only stages with no dedicated preparation flow fall back to plain text.
  String? _stagePrepHint(ApplicationStage stage) {
    switch (stage) {
      case ApplicationStage.medical:
        return "Keep any requested medical/documentation paperwork ready for this stage.";
      default:
        return null;
    }
  }
}

/// Real "Interview Preparation" card (spec §29) for interview/final-interview/recruiter-screen/
/// assessment-centre stages: readiness, questions practiced, STAR stories ready, and a
/// "Continue Preparation" button — preparing here never mutates the application's real stage.
class _InterviewPrepCard extends ConsumerWidget {
  const _InterviewPrepCard({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readinessAsync = ref.watch(interviewReadinessProvider(application.id));
    final analyticsAsync = ref.watch(interviewAnalyticsProvider);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.purple.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.groups_2_outlined, size: 18, color: AppColors.purple),
              SizedBox(width: 8),
              Text("Interview Preparation", style: TextStyle(fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            "Practicing here never changes this application's stage — update it yourself once you've "
            "completed the employer's real interview.",
            style: TextStyle(fontSize: 12, color: AppColors.muted),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: readinessAsync.when(
                  loading: () => const _MiniPrepStat(label: "Readiness", value: "—"),
                  error: (_, __) => const _MiniPrepStat(label: "Readiness", value: "—"),
                  data: (r) => _MiniPrepStat(label: "Readiness", value: r.insufficientData || r.overall == null ? "N/A" : "${r.overall!.round()}%"),
                ),
              ),
              Expanded(
                child: analyticsAsync.when(
                  loading: () => const _MiniPrepStat(label: "Questions", value: "—"),
                  error: (_, __) => const _MiniPrepStat(label: "Questions", value: "—"),
                  data: (a) => _MiniPrepStat(label: "Questions", value: "${a.questionsPracticed}"),
                ),
              ),
              Expanded(
                child: analyticsAsync.when(
                  loading: () => const _MiniPrepStat(label: "STAR Ready", value: "—"),
                  error: (_, __) => const _MiniPrepStat(label: "STAR Ready", value: "—"),
                  data: (a) => _MiniPrepStat(label: "STAR Ready", value: "${a.starStoriesReady}"),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              if (application.jobId != null) ...[
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => context.push("/prepare/interview/company-prep/${application.id}"),
                    child: const Text("Company Research"),
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Expanded(
                flex: 2,
                child: ElevatedButton(
                  onPressed: () => context.push(
                    "/prepare/interview/configure",
                    extra: InterviewConfigureArgs(initialMode: InterviewSessionMode.practice, applicationId: application.id),
                  ),
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.purple),
                  child: const Text("Continue Preparation"),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniPrepStat extends StatelessWidget {
  const _MiniPrepStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
        Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 10)),
      ],
    );
  }
}

class _DetailsTab extends StatelessWidget {
  const _DetailsTab({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, String?)>[
      ("Location", application.location),
      ("Applied", application.appliedDate != null ? DateFormat.yMMMd().format(application.appliedDate!) : null),
      ("Deadline", application.deadline != null ? DateFormat.yMMMd().format(application.deadline!) : null),
      (
        "Interview date",
        application.interviewDate != null ? DateFormat.yMMMd().add_jm().format(application.interviewDate!) : null,
      ),
      (
        "Assessment date",
        application.assessmentDate != null ? DateFormat.yMMMd().add_jm().format(application.assessmentDate!) : null,
      ),
      ("Salary", application.salary),
      ("Contact", application.contactName),
      ("Contact email", application.contactEmail),
    ].where((e) => e.$2 != null).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(width: 130, child: Text(row.$1, style: const TextStyle(color: AppColors.muted))),
                  Expanded(child: Text(row.$2!)),
                ],
              ),
            ),
          if (application.coverLetterText != null) ...[
            const SizedBox(height: 12),
            Text("Cover Letter", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(application.coverLetterText!),
          ],
          if (rows.isEmpty && application.coverLetterText == null)
            const Text("No additional details yet.", style: TextStyle(color: AppColors.muted)),
        ],
      ),
    );
  }
}

class _TimelineTab extends StatelessWidget {
  const _TimelineTab({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    if (application.timeline.isEmpty) {
      return const Center(child: Text("No history yet.", style: TextStyle(color: AppColors.muted)));
    }
    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: application.timeline.length,
      itemBuilder: (context, index) {
        // Oldest first from the API — show newest first, which reads more naturally as a feed.
        final event = application.timeline[application.timeline.length - 1 - index];
        final isLatest = index == 0;
        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                children: [
                  Icon(
                    isLatest ? Icons.radio_button_checked : Icons.check_circle,
                    size: 18,
                    color: isLatest ? AppColors.blue : AppColors.success,
                  ),
                  if (index != application.timeline.length - 1)
                    Container(width: 2, height: 32, color: AppColors.muted.withValues(alpha: 0.2)),
                ],
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(event.stage.label, style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text(
                      DateFormat.yMMMd().add_jm().format(event.occurredAt),
                      style: const TextStyle(fontSize: 12, color: AppColors.muted),
                    ),
                    if (event.note != null) ...[
                      const SizedBox(height: 4),
                      Text(event.note!),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
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
    return Column(
      children: [
        Expanded(
          child: widget.application.notes.isEmpty
              ? const Center(child: Text("No notes yet.", style: TextStyle(color: AppColors.muted)))
              : ListView.separated(
                  padding: const EdgeInsets.all(20),
                  itemCount: widget.application.notes.length,
                  separatorBuilder: (context, index) => const Divider(),
                  itemBuilder: (context, index) {
                    final note = widget.application.notes[index];
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(note.text),
                        const SizedBox(height: 4),
                        Text(
                          DateFormat.yMMMd().add_jm().format(note.createdAt),
                          style: const TextStyle(fontSize: 11, color: AppColors.muted),
                        ),
                      ],
                    );
                  },
                ),
        ),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _noteController,
                  decoration: const InputDecoration(hintText: "Add a note..."),
                ),
              ),
              IconButton(
                onPressed: _adding ? null : _addNote,
                icon: _adding
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.send, color: AppColors.blue),
              ),
            ],
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
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text(e.userMessage, style: const TextStyle(color: AppColors.danger))),
      data: (events) {
        if (events.isEmpty) {
          return const Center(child: Text("No recruitment emails matched to this application yet.", style: TextStyle(color: AppColors.muted)));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(20),
          itemCount: events.length,
          separatorBuilder: (context, index) => const Divider(),
          itemBuilder: (context, index) {
            final event = events[index];
            return ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(event.detectedStage != null ? "${event.detectedStage!.label} update" : "Recruitment email"),
              subtitle: Text(
                "${DateFormat.yMMMd().format(event.receivedAt)} · ${event.confidenceLabel ?? ''} ${_statusLabel(event.status)}".trim(),
                style: const TextStyle(fontSize: 12),
              ),
              onTap: () => context.push("/settings/tracking/events/${event.id}"),
            );
          },
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
}
