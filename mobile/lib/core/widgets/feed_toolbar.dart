import "package:flutter/material.dart";

import "../design/design.dart";
import "app_search_field.dart";

/// Search + horizontally scrolling quick filters + a "Filters" entry point that opens advanced
/// refinements (progressive disclosure). Shared by every feed so they behave identically.
class FeedToolbar extends StatelessWidget {
  const FeedToolbar({
    super.key,
    this.searchHint,
    this.searchController,
    this.onSearchSubmitted,
    this.quickFilters = const [],
    this.onOpenFilters,
    this.activeFilterCount = 0,
  });

  /// Null hides the search field.
  final String? searchHint;
  final TextEditingController? searchController;
  final ValueChanged<String>? onSearchSubmitted;
  final List<Widget> quickFilters;
  final VoidCallback? onOpenFilters;
  final int activeFilterCount;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (searchHint != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.sm, AppSpacing.pageH, 0),
            child: AppSearchField(
              hintText: searchHint!,
              controller: searchController,
              onSubmitted: onSearchSubmitted,
              onCleared: () => onSearchSubmitted?.call(""),
            ),
          ),
        SizedBox(
          height: 56,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xxs),
            children: [
              if (onOpenFilters != null)
                Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.xs),
                  child: ActionChip(
                    avatar: Icon(AppIcons.filter, size: 16, color: activeFilterCount > 0 ? colors.primary : colors.textPrimary),
                    label: Text(activeFilterCount > 0 ? "Filters · $activeFilterCount" : "Filters"),
                    labelStyle: context.text.labelMedium?.copyWith(
                      color: activeFilterCount > 0 ? colors.primary : colors.textPrimary,
                    ),
                    backgroundColor: activeFilterCount > 0 ? colors.tint(colors.primary) : colors.surface,
                    side: BorderSide(color: activeFilterCount > 0 ? colors.primary.withValues(alpha: 0.5) : colors.border),
                    shape: const StadiumBorder(),
                    onPressed: onOpenFilters,
                  ),
                ),
              for (final chip in quickFilters)
                Padding(padding: const EdgeInsets.only(right: AppSpacing.xs), child: chip),
            ],
          ),
        ),
      ],
    );
  }
}

/// Titled group of selectable options inside a filter sheet.
class FilterOptionGroup extends StatelessWidget {
  const FilterOptionGroup({
    super.key,
    required this.title,
    required this.options,
    required this.selected,
    required this.onChanged,
    this.labelFor,
  });

  final String title;
  final List<String> options;
  final String? selected;

  /// Called with the tapped value, or "" when the selected option is tapped again (clear).
  final ValueChanged<String> onChanged;
  final String Function(String value)? labelFor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: context.text.titleSmall),
          Gap.xs,
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              for (final option in options)
                ChoiceChip(
                  label: Text(labelFor?.call(option) ?? option),
                  selected: selected == option,
                  onSelected: (_) => onChanged(selected == option ? "" : option),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
