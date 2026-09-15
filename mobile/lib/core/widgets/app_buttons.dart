import "package:flutter/material.dart";

import "../design/design.dart";

/// Label + optional leading icon, or a spinner while loading. Shared by every CareerOS button so
/// loading/icon behaviour is identical everywhere.
class _ButtonContent extends StatelessWidget {
  const _ButtonContent({required this.label, this.icon, required this.isLoading, required this.spinnerColor});

  final String label;
  final IconData? icon;
  final bool isLoading;
  final Color spinnerColor;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return SizedBox.square(
        dimension: 20,
        child: CircularProgressIndicator(strokeWidth: 2.2, color: spinnerColor),
      );
    }
    final text = Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center);
    if (icon == null) return text;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 20),
        Gap.xs,
        Flexible(child: text),
      ],
    );
  }
}

Widget _sized({required bool expand, required Widget child}) =>
    expand ? SizedBox(width: double.infinity, child: child) : child;

/// The one dominant action on a screen.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    return _sized(
      expand: expand,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        child: _ButtonContent(label: label, icon: icon, isLoading: isLoading, spinnerColor: context.colors.textSecondary),
      ),
    );
  }
}

/// Supporting action with a tinted background — clearly weaker than [PrimaryButton].
class SecondaryButton extends StatelessWidget {
  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return _sized(
      expand: expand,
      child: FilledButton.tonal(
        style: FilledButton.styleFrom(
          backgroundColor: colors.tint(colors.primary),
          foregroundColor: colors.primary,
          disabledBackgroundColor: colors.surfaceMuted,
        ),
        onPressed: isLoading ? null : onPressed,
        child: _ButtonContent(label: label, icon: icon, isLoading: isLoading, spinnerColor: colors.primary),
      ),
    );
  }
}

/// Neutral bordered action (e.g. "Save" next to "Apply").
class AppOutlineButton extends StatelessWidget {
  const AppOutlineButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    return _sized(
      expand: expand,
      child: OutlinedButton(
        onPressed: isLoading ? null : onPressed,
        child: _ButtonContent(label: label, icon: icon, isLoading: isLoading, spinnerColor: context.colors.primary),
      ),
    );
  }
}

/// Destructive confirmation (delete account, discard session).
class DangerButton extends StatelessWidget {
  const DangerButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expand = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    return _sized(
      expand: expand,
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(backgroundColor: AppColors.error, foregroundColor: Colors.white),
        onPressed: isLoading ? null : onPressed,
        child: _ButtonContent(label: label, icon: icon, isLoading: isLoading, spinnerColor: Colors.white),
      ),
    );
  }
}

/// Tertiary, inline action ("View all", "Review").
class AppTextButton extends StatelessWidget {
  const AppTextButton({super.key, required this.label, required this.onPressed, this.icon, this.tone});

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final AppTone? tone;

  @override
  Widget build(BuildContext context) {
    final color = tone?.color(context);
    return TextButton(
      style: color == null ? null : TextButton.styleFrom(foregroundColor: color),
      onPressed: onPressed,
      child: _ButtonContent(label: label, icon: icon, isLoading: false, spinnerColor: context.colors.primary),
    );
  }
}
