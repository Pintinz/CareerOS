import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../data/application_models.dart";
import "stage_badge.dart";

/// Bottom sheet returning the (stage, note) the user picked, or null if cancelled. The caller
/// is responsible for actually calling the API — this widget has no side effects of its own.
Future<(ApplicationStage, String?)?> showUpdateStageSheet(BuildContext context, ApplicationStage current) {
  return showModalBottomSheet<(ApplicationStage, String?)>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => _UpdateStageSheet(current: current),
  );
}

class _UpdateStageSheet extends StatefulWidget {
  const _UpdateStageSheet({required this.current});

  final ApplicationStage current;

  @override
  State<_UpdateStageSheet> createState() => _UpdateStageSheetState();
}

class _UpdateStageSheetState extends State<_UpdateStageSheet> {
  late ApplicationStage _selected = widget.current;
  final _noteController = TextEditingController();

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: DraggableScrollableSheet(
        initialChildSize: 0.75,
        maxChildSize: 0.92,
        expand: false,
        builder: (context, scrollController) => Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, 0, AppSpacing.pageH, AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text("Update Stage", style: context.text.titleLarge),
              const SizedBox(height: 2),
              Text("Record where this application stands now. Your history is kept.", style: context.text.bodySmall),
              Gap.sm,
              Expanded(
                child: RadioGroup<ApplicationStage>(
                  groupValue: _selected,
                  onChanged: (value) => setState(() => _selected = value!),
                  child: ListView(
                    controller: scrollController,
                    children: [
                      for (final stage in ApplicationStage.values)
                        RadioListTile<ApplicationStage>(
                          value: stage,
                          contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                          controlAffinity: ListTileControlAffinity.trailing,
                          selected: stage == _selected,
                          selectedTileColor: colors.tint(colors.primary),
                          shape: const RoundedRectangleBorder(borderRadius: AppRadius.mdAll),
                          secondary: IconTile(icon: stageIcon(stage), tone: stageTone(stage), size: 36),
                          title: Row(
                            children: [
                              Flexible(child: Text(stage.label, style: context.text.titleSmall)),
                              if (stage == widget.current) ...[
                                Gap.xs,
                                const StatusChip(label: "Current", dense: true),
                              ],
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              Gap.sm,
              TextField(
                controller: _noteController,
                decoration: const InputDecoration(labelText: "Note (optional)", prefixIcon: Icon(Icons.sticky_note_2_outlined)),
              ),
              Gap.sm,
              PrimaryButton(label: "Save", onPressed: () => Navigator.of(context).pop((_selected, _noteController.text.trim()))),
            ],
          ),
        ),
      ),
    );
  }
}
