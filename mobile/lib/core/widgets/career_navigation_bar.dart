import "package:flutter/material.dart";

import "../design/design.dart";

class CareerNavItem {
  const CareerNavItem({required this.icon, required this.selectedIcon, required this.label});

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

/// Bottom navigation for the five hubs. Unlike Material's NavigationBar, labels scale down to fit
/// on narrow phones instead of wrapping ("Opportunities" at 320–360dp), and every item keeps a
/// 48dp+ touch target with selected-state semantics.
class CareerNavigationBar extends StatelessWidget {
  const CareerNavigationBar({super.key, required this.items, required this.selectedIndex, required this.onSelected});

  final List<CareerNavItem> items;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return DecoratedBox(
      decoration: BoxDecoration(color: colors.surface, border: Border(top: BorderSide(color: colors.border))),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 68,
          child: Row(
            children: [
              for (final (i, item) in items.indexed)
                Expanded(
                  child: _NavButton(
                    item: item,
                    selected: i == selectedIndex,
                    position: "${i + 1} of ${items.length}",
                    onTap: () => onSelected(i),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({required this.item, required this.selected, required this.position, required this.onTap});

  final CareerNavItem item;
  final bool selected;
  final String position;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final color = selected ? colors.primary : colors.textSecondary;
    return Semantics(
      button: true,
      selected: selected,
      label: "${item.label}, tab $position",
      excludeSemantics: true,
      child: InkResponse(
        onTap: onTap,
        highlightShape: BoxShape.rectangle,
        containedInkWell: true,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2, vertical: AppSpacing.xs),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedContainer(
                duration: AppMotion.of(context, AppMotion.fast),
                curve: AppMotion.curve,
                width: 56,
                height: 30,
                decoration: BoxDecoration(
                  color: selected ? colors.tint(colors.primary) : Colors.transparent,
                  borderRadius: AppRadius.pillAll,
                ),
                alignment: Alignment.center,
                child: Icon(selected ? item.selectedIcon : item.icon, color: color, size: 24),
              ),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  item.label,
                  maxLines: 1,
                  style: context.text.labelSmall?.copyWith(
                    color: color,
                    fontSize: 11.5,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
