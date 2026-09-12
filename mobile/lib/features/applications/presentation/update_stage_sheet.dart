import "package:flutter/material.dart";

import "../../../theme/app_colors.dart";
import "../data/application_models.dart";

/// Bottom sheet returning the (stage, note) the user picked, or null if cancelled. The caller
/// is responsible for actually calling the API — this widget has no side effects of its own.
Future<(ApplicationStage, String?)?> showUpdateStageSheet(BuildContext context, ApplicationStage current) {
  return showModalBottomSheet<(ApplicationStage, String?)>(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
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
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Update Stage", style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 12),
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
                          title: Row(
                            children: [
                              Text(stage.label),
                              const SizedBox(width: 8),
                              if (stage == widget.current)
                                const Text("(current)", style: TextStyle(fontSize: 11, color: AppColors.muted)),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              TextField(
                controller: _noteController,
                decoration: const InputDecoration(labelText: "Note (optional)"),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.of(context).pop((_selected, _noteController.text.trim())),
                  child: const Text("Save"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
