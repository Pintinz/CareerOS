import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/profile_repository.dart";
import "profile_providers.dart";

/// Edits the real profile fields the backend stores. Empty fields are sent as null (cleared).
Future<void> showEditProfileSheet(BuildContext context, UserProfile profile) {
  return showCareerBottomSheet<void>(
    context: context,
    title: "Edit profile",
    builder: (_) => _EditProfileForm(profile: profile),
  );
}

class _EditProfileForm extends ConsumerStatefulWidget {
  const _EditProfileForm({required this.profile});

  final UserProfile profile;

  @override
  ConsumerState<_EditProfileForm> createState() => _EditProfileFormState();
}

class _EditProfileFormState extends ConsumerState<_EditProfileForm> {
  final _formKey = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.profile.fullName);
  late final _title = TextEditingController(text: widget.profile.professionalTitle);
  late final _location = TextEditingController(text: widget.profile.location);
  late final _years = TextEditingController(text: widget.profile.yearsOfExperience?.toString());
  late final _education = TextEditingController(text: widget.profile.highestEducation);
  late final _field = TextEditingController(text: widget.profile.fieldOfStudy);
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_name, _title, _location, _years, _education, _field]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _text(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(profileRepositoryProvider).updateProfileFields({
        "full_name": _text(_name),
        "professional_title": _text(_title),
        "location": _text(_location),
        "years_of_experience": _years.text.trim().isEmpty ? null : int.parse(_years.text.trim()),
        "highest_education": _text(_education),
        "field_of_study": _text(_field),
      });
      ref.invalidate(userProfileProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = e.userMessage);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    InputDecoration deco(String label, IconData icon) => InputDecoration(labelText: label, prefixIcon: Icon(icon));
    return SingleChildScrollView(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextFormField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.name],
              decoration: deco("Full name", AppIcons.profile),
            ),
            Gap.sm,
            TextFormField(
              controller: _title,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              decoration: deco("Professional title", AppIcons.job),
            ),
            Gap.sm,
            TextFormField(
              controller: _location,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              decoration: deco("Location", AppIcons.location),
            ),
            Gap.sm,
            TextFormField(
              controller: _years,
              keyboardType: TextInputType.number,
              textInputAction: TextInputAction.next,
              decoration: deco("Years of experience", Icons.timelapse_rounded),
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                final n = int.tryParse(v.trim());
                return n == null || n < 0 || n > 70 ? "Enter a whole number of years" : null;
              },
            ),
            Gap.sm,
            TextFormField(
              controller: _education,
              textCapitalization: TextCapitalization.sentences,
              textInputAction: TextInputAction.next,
              decoration: deco("Highest education", AppIcons.scholarship),
            ),
            Gap.sm,
            TextFormField(
              controller: _field,
              textCapitalization: TextCapitalization.sentences,
              textInputAction: TextInputAction.done,
              decoration: deco("Field of study", Icons.menu_book_rounded),
            ),
            if (_error != null) ...[
              Gap.sm,
              Text(_error!, style: context.text.bodyMedium?.copyWith(color: AppColors.error)),
            ],
            Gap.lg,
            PrimaryButton(label: "Save Profile", isLoading: _saving, onPressed: _save),
          ],
        ),
      ),
    );
  }
}
