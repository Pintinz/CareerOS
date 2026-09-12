import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../theme/app_colors.dart";
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
    _tabController = TabController(length: 3, vsync: this);
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
            if (_stagePrepHint(application.currentStage) != null)
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
              tabs: const [Tab(text: "Details"), Tab(text: "Timeline"), Tab(text: "Notes")],
            ),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _DetailsTab(application: application),
                  _TimelineTab(application: application),
                  _NotesTab(application: application),
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

  /// Spec §38: stage-aware preparation hints. Phases 6/7 (aptitude/interview prep) aren't built
  /// yet, so this is informational text only — no dead "Prepare" button pointing nowhere.
  String? _stagePrepHint(ApplicationStage stage) {
    switch (stage) {
      case ApplicationStage.aptitudeTest:
        return "Aptitude test preparation is coming in a future update.";
      case ApplicationStage.interview:
      case ApplicationStage.finalInterview:
        return "Interview preparation is coming in a future update.";
      case ApplicationStage.medical:
        return "Keep any requested medical/documentation paperwork ready for this stage.";
      default:
        return null;
    }
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
