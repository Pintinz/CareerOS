import "package:flutter/material.dart";

import "../design/design.dart";

/// Rounded search input with a clear button. Debounce/submit behaviour stays with the caller.
class AppSearchField extends StatefulWidget {
  const AppSearchField({
    super.key,
    required this.hintText,
    this.controller,
    this.onChanged,
    this.onSubmitted,
    this.onCleared,
  });

  final String hintText;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final VoidCallback? onCleared;

  @override
  State<AppSearchField> createState() => _AppSearchFieldState();
}

class _AppSearchFieldState extends State<AppSearchField> {
  late final TextEditingController _controller = widget.controller ?? TextEditingController();

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() => setState(() {});

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    if (widget.controller == null) _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return TextField(
      controller: _controller,
      onChanged: widget.onChanged,
      onSubmitted: widget.onSubmitted,
      textInputAction: TextInputAction.search,
      style: context.text.bodyLarge,
      decoration: InputDecoration(
        hintText: widget.hintText,
        prefixIcon: const Icon(AppIcons.search),
        fillColor: colors.surface,
        border: OutlineInputBorder(borderRadius: AppRadius.buttonAll, borderSide: BorderSide(color: colors.border)),
        enabledBorder: OutlineInputBorder(borderRadius: AppRadius.buttonAll, borderSide: BorderSide(color: colors.border)),
        focusedBorder: OutlineInputBorder(borderRadius: AppRadius.buttonAll, borderSide: BorderSide(color: colors.primary, width: 1.5)),
        suffixIcon: _controller.text.isEmpty
            ? null
            : IconButton(
                tooltip: "Clear search",
                icon: const Icon(Icons.close_rounded),
                onPressed: () {
                  _controller.clear();
                  widget.onChanged?.call("");
                  widget.onCleared?.call();
                },
              ),
      ),
    );
  }
}
