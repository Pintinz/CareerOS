import "package:file_picker/file_picker.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "ats_providers.dart";
import "ats_result_view.dart";

/// Arguments passed via GoRouter `extra` when navigating here from a job's "Analyze CV" button.
class AtsAnalyzeArgs {
  const AtsAnalyzeArgs({this.jobId, this.jobTitle});

  final String? jobId;
  final String? jobTitle;
}

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
      await controller.analyze(
        cvDocumentId: _selectedCvId,
        jobDescription: _jobDescriptionController.text,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final cvsAsync = ref.watch(cvListProvider);
    final analysisState = ref.watch(atsAnalysisControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Analyze CV")),
      body: analysisState.value != null
          ? AtsResultView(
              analysis: analysisState.value!,
              onAnalyzeAgain: () => ref.read(atsAnalysisControllerProvider.notifier).reset(),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (widget.args?.jobTitle != null) ...[
                    Text("Analyzing against:", style: Theme.of(context).textTheme.bodyMedium),
                    Text(widget.args!.jobTitle!, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 20),
                  ],
                  Text("1. Choose a CV", style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  cvsAsync.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
                    data: (cvs) => RadioGroup<String>(
                      groupValue: _selectedCvId,
                      onChanged: (value) => setState(() => _selectedCvId = value),
                      child: Column(
                        children: [
                          for (final cv in cvs)
                            RadioListTile<String>(
                              value: cv.id,
                              title: Text(cv.name),
                              subtitle: cv.isPrimary ? const Text("Primary CV") : null,
                            ),
                          if (cvs.isEmpty)
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 8),
                              child: Text("No CVs uploaded yet.", style: TextStyle(color: AppColors.muted)),
                            ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _uploading ? null : _uploadNewCv,
                    icon: _uploading
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.upload_file),
                    label: Text(_uploading ? "Uploading..." : "Upload a new CV (PDF, DOCX, or TXT)"),
                  ),
                  if (_uploadError != null) ...[
                    const SizedBox(height: 8),
                    Text(_uploadError!, style: const TextStyle(color: AppColors.danger)),
                  ],
                  if (!_hasJob) ...[
                    const SizedBox(height: 24),
                    Text("2. Paste the job description", style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _jobDescriptionController,
                      maxLines: 6,
                      decoration: const InputDecoration(hintText: "Paste the job description here..."),
                    ),
                  ],
                  const SizedBox(height: 24),
                  if (analysisState.hasError)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text(analysisState.error!.userMessage, style: const TextStyle(color: AppColors.danger)),
                    ),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: analysisState.isLoading || _selectedCvId == null ? null : _runAnalysis,
                      child: analysisState.isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text("Analyze"),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
