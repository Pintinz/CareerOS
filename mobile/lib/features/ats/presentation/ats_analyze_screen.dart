import "dart:async";

import "package:file_picker/file_picker.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/monetization/ad_placement.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "ats_providers.dart";
import "ats_result_view.dart";

/// Arguments passed via GoRouter `extra` when navigating here from a job's "Analyze CV" button.
class AtsAnalyzeArgs {
  const AtsAnalyzeArgs({this.jobId, this.jobTitle});

  final String? jobId;
  final String? jobTitle;
}

/// CV & Career Tools → Analyze CV. Rules-based ATS readiness against a listed job or a pasted
/// job description. Only implemented tools are offered.
class AtsAnalyzeScreen extends ConsumerStatefulWidget {
  const AtsAnalyzeScreen({super.key, this.args});

  final AtsAnalyzeArgs? args;

  @override
  ConsumerState<AtsAnalyzeScreen> createState() => _AtsAnalyzeScreenState();
}

class _AtsAnalyzeScreenState extends ConsumerState<AtsAnalyzeScreen> {
  String? _selectedCvId;
  final _jobDescriptionController = TextEditingController();
  bool _uploading = false;
  String? _uploadError;

  bool get _hasJob => widget.args?.jobId != null;

  @override
  void dispose() {
    _jobDescriptionController.dispose();
    super.dispose();
  }

  Future<void> _uploadNewCv() async {
    final file = await FilePicker.pickFile(type: FileType.custom, allowedExtensions: ["pdf", "docx", "txt"]);
    if (file?.path == null) return;

    setState(() {
      _uploading = true;
      _uploadError = null;
    });
    try {
      final cv = await ref.read(atsRepositoryProvider).uploadCv(filePath: file!.path!, filename: file.name);
      ref.invalidate(cvListProvider);
      setState(() => _selectedCvId = cv.id);
    } catch (e) {
      setState(() => _uploadError = e.userMessage);
    } finally {
      setState(() => _uploading = false);
    }
  }

  Future<void> _runAnalysis() async {
    if (_selectedCvId == null) return;
    final controller = ref.read(atsAnalysisControllerProvider.notifier);
    if (_hasJob) {
      await controller.analyze(cvDocumentId: _selectedCvId, jobId: widget.args!.jobId);
    } else {
      await controller.analyze(cvDocumentId: _selectedCvId, jobDescription: _jobDescriptionController.text);
    }
    // Spec §18: a natural pause point (after the result is already shown), never before/during
    // the analysis itself. AdService's own frequency controller decides whether this actually
    // shows anything — this call is always safe to make.
    if (ref.read(atsAnalysisControllerProvider).hasValue) {
      unawaited(ref.read(adServiceProvider).maybeShowInterstitial(placement: AdPlacement.atsResults));
    }
  }

  @override
  Widget build(BuildContext context) {
    final cvsAsync = ref.watch(cvListProvider);
    final analysisState = ref.watch(atsAnalysisControllerProvider);
    final colors = context.colors;

    if (analysisState.value != null) {
      return Scaffold(
        appBar: AppBar(title: const Text("CV Analysis")),
        body: AtsResultView(
          analysis: analysisState.value!,
          onAnalyzeAgain: () => ref.read(atsAnalysisControllerProvider.notifier).reset(),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text("CV & Career Tools")),
      bottomNavigationBar: BottomActionBar(
        primary: PrimaryButton(
          label: "Analyze CV",
          icon: Icons.document_scanner_outlined,
          isLoading: analysisState.isLoading,
          onPressed: _selectedCvId == null ? null : _runAnalysis,
        ),
      ),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          CareerCard(
            variant: CareerCardVariant.feature,
            child: Row(
              children: [
                const IconTile(icon: AppIcons.cv, tone: AppTone.purple, size: 52),
                Gap.md,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Analyze CV", style: context.text.titleLarge),
                      const SizedBox(height: 2),
                      Text(
                        "See how your CV reads to applicant tracking systems and which keywords a role expects.",
                        style: context.text.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (widget.args?.jobTitle != null) ...[
            Gap.md,
            InsightCard(icon: AppIcons.job, title: "Matching against", message: widget.args!.jobTitle!),
          ],
          Gap.xl,
          const _StepHeader(number: 1, title: "Choose a CV"),
          Gap.sm,
          cvsAsync.when(
            loading: () => const SkeletonCard(),
            error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(cvListProvider)),
            data: (cvs) => cvs.isEmpty
                ? CareerCard(
                    variant: CareerCardVariant.muted,
                    child: Row(
                      children: [
                        const IconTile(icon: Icons.upload_file_rounded, size: 40),
                        Gap.sm,
                        Expanded(child: Text("No CVs uploaded yet. Upload one to get started.", style: context.text.bodyMedium)),
                      ],
                    ),
                  )
                : RadioGroup<String>(
                    groupValue: _selectedCvId,
                    onChanged: (value) => setState(() => _selectedCvId = value),
                    child: Material(
                      color: colors.surface,
                      shape: RoundedRectangleBorder(borderRadius: AppRadius.cardAll, side: BorderSide(color: colors.border)),
                      clipBehavior: Clip.antiAlias,
                      child: Column(
                        children: [
                          for (final (i, cv) in cvs.indexed) ...[
                            if (i > 0) Divider(height: 1, indent: 56, color: colors.border),
                            RadioListTile<String>(
                              value: cv.id,
                              secondary: const Icon(AppIcons.cv),
                              title: Text(cv.name, style: context.text.titleSmall),
                              subtitle: cv.isPrimary
                                  ? Text("Primary CV", style: context.text.bodySmall?.copyWith(color: colors.primary))
                                  : (cv.originalFilename != null ? Text(cv.originalFilename!, style: context.text.bodySmall) : null),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
          ),
          Gap.sm,
          AppOutlineButton(
            label: _uploading ? "Uploading…" : "Upload a new CV (PDF, DOCX or TXT)",
            icon: Icons.upload_file_rounded,
            isLoading: _uploading,
            onPressed: _uploadNewCv,
          ),
          if (_uploadError != null) ...[
            Gap.xs,
            Text(_uploadError!, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
          ],
          if (!_hasJob) ...[
            Gap.xl,
            const _StepHeader(number: 2, title: "Paste the job description"),
            Gap.xs,
            Text("Adding a job description checks keywords and requirements for that specific role.", style: context.text.bodySmall),
            Gap.sm,
            TextField(
              controller: _jobDescriptionController,
              minLines: 5,
              maxLines: 12,
              decoration: const InputDecoration(hintText: "Paste the job description here…", alignLabelWithHint: true),
            ),
          ],
          if (analysisState.hasError) ...[
            Gap.md,
            Text(analysisState.error!.userMessage, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
          ],
          Gap.lg,
          Text(
            "CareerOS estimates readiness against common ATS parsing patterns. It can't see any employer's own screening system.",
            style: context.text.labelSmall,
          ),
        ],
      ),
    );
  }
}

class _StepHeader extends StatelessWidget {
  const _StepHeader({required this.number, required this.title});

  final int number;
  final String title;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Row(
      children: [
        Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(color: colors.primary, shape: BoxShape.circle),
          alignment: Alignment.center,
          child: Text("$number", style: context.text.labelMedium?.copyWith(color: Colors.white)),
        ),
        Gap.xs,
        Semantics(header: true, child: Text(title, style: context.text.titleMedium)),
      ],
    );
  }
}
