import "package:flutter/material.dart";

import "../design/design.dart";
import "app_buttons.dart";

/// Empty state: icon · title · one helpful sentence · next action. Never "No data found."
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  /// Smaller vertical footprint for use inside a section rather than a whole screen.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: compact ? AppSpacing.lg : AppSpacing.xxxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _StateIllustration(icon: icon, tone: AppTone.primary, compact: compact),
              Gap.lg,
              Text(title, textAlign: TextAlign.center, style: context.text.titleMedium),
              const SizedBox(height: 6),
              Text(message, textAlign: TextAlign.center, style: context.text.bodyMedium),
              if (actionLabel != null && onAction != null) ...[
                Gap.lg,
                PrimaryButton(label: actionLabel!, onPressed: onAction, expand: false),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Soft concentric halo around a state icon — calm and branded, never a cartoon.
class _StateIllustration extends StatelessWidget {
  const _StateIllustration({required this.icon, required this.tone, required this.compact});

  final IconData icon;
  final AppTone tone;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final color = tone.color(context);
    final isDark = context.colors.isDark;
    final outer = compact ? 76.0 : 104.0;
    final inner = compact ? 52.0 : 68.0;
    return ExcludeSemantics(
      child: Container(
        width: outer,
        height: outer,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withValues(alpha: isDark ? 0.08 : 0.05),
          border: Border.all(color: color.withValues(alpha: isDark ? 0.14 : 0.08)),
        ),
        alignment: Alignment.center,
        child: Container(
          width: inner,
          height: inner,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [color.withValues(alpha: isDark ? 0.26 : 0.16), color.withValues(alpha: isDark ? 0.14 : 0.08)],
            ),
          ),
          alignment: Alignment.center,
          child: Icon(icon, size: compact ? 24 : 30, color: color),
        ),
      ),
    );
  }
}

/// Friendly, recoverable error. Pass an already user-safe [message] (see `userMessage`).
class ErrorState extends StatelessWidget {
  const ErrorState({
    super.key,
    this.title = "We couldn't load this section",
    required this.message,
    this.onRetry,
    this.compact = false,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: compact ? AppSpacing.lg : AppSpacing.xxxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Warning rather than red: a failed load is recoverable, not an alarm.
              _StateIllustration(icon: Icons.cloud_off_rounded, tone: AppTone.warning, compact: compact),
              Gap.lg,
              Text(title, textAlign: TextAlign.center, style: context.text.titleMedium),
              const SizedBox(height: 6),
              Text(message, textAlign: TextAlign.center, style: context.text.bodyMedium),
              if (onRetry != null) ...[
                Gap.lg,
                AppOutlineButton(label: "Retry", icon: Icons.refresh_rounded, onPressed: onRetry, expand: false),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// A single pulsing placeholder block.
class LoadingSkeleton extends StatefulWidget {
  const LoadingSkeleton({super.key, this.width, this.height = 14, this.radius = AppRadius.sm, this.circle = false});

  final double? width;
  final double height;
  final double radius;
  final bool circle;

  @override
  State<LoadingSkeleton> createState() => _LoadingSkeletonState();
}

class _LoadingSkeletonState extends State<LoadingSkeleton> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _controller.stop();
    } else if (!_controller.isAnimating) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = context.colors.surfaceMuted;
    return FadeTransition(
      opacity: Tween<double>(begin: 1, end: 0.55).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut)),
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          color: base,
          shape: widget.circle ? BoxShape.circle : BoxShape.rectangle,
          borderRadius: widget.circle ? null : BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}

/// Skeleton shaped like a feed card (logo + two text lines + tags).
class SkeletonCard extends StatelessWidget {
  const SkeletonCard({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: AppSpacing.card,
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: AppRadius.cardAll,
        border: Border.all(color: colors.border),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LoadingSkeleton(width: 48, height: 48, radius: AppRadius.md),
          Gap.sm,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LoadingSkeleton(width: 180, height: 16),
                Gap.xs,
                LoadingSkeleton(width: 120, height: 12),
                Gap.sm,
                Row(
                  children: [
                    LoadingSkeleton(width: 64, height: 20),
                    Gap.xs,
                    LoadingSkeleton(width: 72, height: 20),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A column of [SkeletonCard]s for first-load feeds and lists.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.itemCount = 4, this.padding = AppSpacing.page});

  final int itemCount;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: "Loading",
      child: ListView.separated(
        padding: padding,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: itemCount,
        separatorBuilder: (_, __) => Gap.sm,
        itemBuilder: (_, __) => const SkeletonCard(),
      ),
    );
  }
}
