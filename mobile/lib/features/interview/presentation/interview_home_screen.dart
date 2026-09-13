import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../data/interview_models.dart";
import "interview_configuration_screen.dart";

const _kMainCategories = [
  ("company_specific", "Company Specific", Icons.apartment_outlined),
  ("job_specific", "Job Specific", Icons.work_outline),
  ("technical", "Technical", Icons.build_outlined),
  ("behavioral", "Behavioral", Icons.psychology_outlined),
  ("hr_general", "HR / General", Icons.badge_outlined),
  ("safety", "Safety", Icons.health_and_safety_outlined),
  ("leadership", "Leadership", Icons.emoji_events_outlined),
  ("management", "Management", Icons.groups_outlined),
];

/// "INTERVIEW PREPARATION" home (spec §3): category tiles plus Mock Interview / Question
/// Practice / STAR Story Builder / Company Research / Role Preparation entry points.
class InterviewHomeScreen extends StatelessWidget {
  const InterviewHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Interview Preparation")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text("Quick Start", style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _QuickAction(
                  icon: Icons.quiz_outlined,
                  label: "Mock Interview",
                  onTap: () => context.push(
                    "/prepare/interview/configure",
                    extra: const InterviewConfigureArgs(initialMode: InterviewSessionMode.mock),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _QuickAction(
                  icon: Icons.edit_note_outlined,
                  label: "Question Practice",
                  onTap: () => context.push("/prepare/interview/configure", extra: const InterviewConfigureArgs()),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _QuickAction(
                  icon: Icons.auto_stories_outlined,
                  label: "STAR Story Builder",
                  onTap: () => context.push("/prepare/interview/star-stories"),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _QuickAction(
                  icon: Icons.insights_outlined,
                  label: "Readiness & Analytics",
                  onTap: () => context.push("/prepare/interview/analytics"),
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          Text("Practice by Category", style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.6,
            children: [
              for (final (slug, label, icon) in _kMainCategories)
                _CategoryTile(
                  icon: icon,
                  label: label,
                  onTap: () => context.push(
                    "/prepare/interview/configure",
                    extra: InterviewConfigureArgs(initialCategorySlug: slug),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            "Situational and Career Motivation practice are available from the full category list in Configure.",
            style: TextStyle(color: AppColors.muted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 12),
          child: Column(
            children: [
              Icon(icon, color: AppColors.blue, size: 28),
              const SizedBox(height: 8),
              Text(label, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            ],
          ),
        ),
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Icon(icon, color: AppColors.purple),
              const SizedBox(width: 10),
              Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
            ],
          ),
        ),
      ),
    );
  }
}
