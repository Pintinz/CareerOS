import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "application_providers.dart";

class CreateApplicationScreen extends ConsumerStatefulWidget {
  const CreateApplicationScreen({super.key});

  @override
  ConsumerState<CreateApplicationScreen> createState() => _CreateApplicationScreenState();
}

class _CreateApplicationScreenState extends ConsumerState<CreateApplicationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _companyController = TextEditingController();
  final _roleController = TextEditingController();
  final _locationController = TextEditingController();
  final _jobUrlController = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _companyController.dispose();
    _roleController.dispose();
    _locationController.dispose();
    _jobUrlController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final application = await ref.read(applicationRepositoryProvider).createManual(
            companyName: _companyController.text.trim(),
            roleTitle: _roleController.text.trim(),
            location: _locationController.text.trim(),
            jobUrl: _jobUrlController.text.trim(),
          );
      ref.read(applicationListProvider.notifier).refresh();
      if (mounted) context.replace("/applications/${application.id}");
    } catch (e) {
      setState(() => _error = e.userMessage);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Track an Application")),
      bottomNavigationBar: BottomActionBar(primary: PrimaryButton(label: "Start Tracking", isLoading: _saving, onPressed: _submit)),
      body: SingleChildScrollView(
        padding: AppSpacing.page,
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const InsightCard(
                icon: AppIcons.application,
                title: "Applied somewhere else?",
                message: "Track roles that aren't listed in CareerOS. For listed jobs, use Track Application on the job page.",
              ),
              Gap.xl,
              Text("Role", style: context.text.titleMedium),
              Gap.sm,
              TextFormField(
                controller: _companyController,
                textInputAction: TextInputAction.next,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: "Company", prefixIcon: Icon(AppIcons.company)),
                validator: (v) => (v == null || v.trim().isEmpty) ? "Required" : null,
              ),
              Gap.md,
              TextFormField(
                controller: _roleController,
                textInputAction: TextInputAction.next,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: "Role title", prefixIcon: Icon(AppIcons.job)),
                validator: (v) => (v == null || v.trim().isEmpty) ? "Required" : null,
              ),
              Gap.xl,
              Text("Optional details", style: context.text.titleMedium),
              Gap.sm,
              TextFormField(
                controller: _locationController,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: "Location", prefixIcon: Icon(AppIcons.location)),
              ),
              Gap.md,
              TextFormField(
                controller: _jobUrlController,
                keyboardType: TextInputType.url,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _saving ? null : _submit(),
                decoration: const InputDecoration(labelText: "Job posting URL", prefixIcon: Icon(Icons.link_rounded)),
              ),
              if (_error != null) ...[
                Gap.md,
                Text(_error!, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
