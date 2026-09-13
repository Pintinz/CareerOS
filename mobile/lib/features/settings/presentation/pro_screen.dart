import "package:flutter/material.dart";

import "../../../theme/app_colors.dart";

/// Settings → CareerOS Pro (spec §10/§57). No purchase flow exists — this screen must never
/// imply one does. Shows the prepared entitlement architecture (ad-free, unlimited usage,
/// advanced analytics) honestly labeled "Coming Soon", with no button that looks purchasable.
class ProScreen extends StatelessWidget {
  const ProScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("CareerOS Pro")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            color: AppColors.blue.withValues(alpha: 0.06),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.workspace_premium_outlined, color: AppColors.blue, size: 28),
                      const SizedBox(width: 10),
                      Text("CareerOS Pro", style: Theme.of(context).textTheme.titleLarge),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const _ComingSoonBadge(),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          const _ProFeatureTile(icon: Icons.block_outlined, title: "No ads"),
          const _ProFeatureTile(icon: Icons.fact_check_outlined, title: "Unlimited ATS analyses"),
          const _ProFeatureTile(icon: Icons.quiz_outlined, title: "Unlimited aptitude tests"),
          const _ProFeatureTile(icon: Icons.insights_outlined, title: "Advanced analytics"),
          const _ProFeatureTile(icon: Icons.school_outlined, title: "Premium interview practice content"),
          const _ProFeatureTile(icon: Icons.description_outlined, title: "Multiple CV features"),
          const SizedBox(height: 20),
          Text(
            "CareerOS Pro purchases are not yet available. This screen shows what's planned — "
            "there is nothing to buy here yet, and nothing on this screen will charge you.",
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
          ),
        ],
      ),
    );
  }
}

class _ComingSoonBadge extends StatelessWidget {
  const _ComingSoonBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: AppColors.muted.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
      child: const Text("Coming Soon", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.muted)),
    );
  }
}

class _ProFeatureTile extends StatelessWidget {
  const _ProFeatureTile({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.muted),
      title: Text(title),
    );
  }
}
