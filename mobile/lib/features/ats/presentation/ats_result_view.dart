import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../data/ats_models.dart";

/// ATS results (spec §35): readiness score → breakdown → strengths → missing keywords →
/// recommended improvements. Rules-based; never claims to replicate an employer's ATS.
class AtsResultView extends StatelessWidget {
  const AtsResultView({super.key, required this.analysis, this.onAnalyzeAgain});

  final AtsAnalysis analysis;
  final VoidCallback? onAnalyzeAgain;

  AppTone get _tone {
    if (analysis.overallScore >= 75) return AppTone.success;
    if (analysis.overallScore >= 50) return AppTone.warning;
    return AppTone.danger;
  }

  String get _label {
    if (analysis.overallScore >= 75) return "Strong readiness";
    if (analysis.overallScore >= 50) return "Room to improve";
    return "Needs work";
  }

  @override
  Widget build(BuildContext context) {
    final improvements = [
      ...analysis.formattingIssues,
      if (analysis.missingMetricsNote != null) analysis.missingMetricsNote!,
    ];

    return ListView(
      padding: AppSpacing.page,
      children: [
        CareerCard(
          variant: CareerCardVariant.feature,
          child: Column(
            children: [
              CareerProgressRing(
                value: analysis.overallScore / 100,
                size: 140,
                strokeWidth: 13,
                tone: _tone,
                semanticLabel: "ATS readiness score",
                semanticValue: "${analysis.overallScore} out of 100",
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text("${analysis.overallScore}", style: context.text.displaySmall),
                    Text("out of 100", style: context.text.bodySmall),
                  ],
                ),
              ),
              Gap.md,
              Text(analysis.jobTitle != null ? "Job Match Score" : "ATS Readiness Score", style: context.text.titleLarge),
              if (analysis.jobTitle != null) ...[
                const SizedBox(height: 2),
                Text("for ${analysis.jobTitle}", style: context.text.bodyMedium, textAlign: TextAlign.center),
              ],
              Gap.xs,
              StatusChip(label: _label, tone: _tone),
              Gap.sm,
              Text(
                "Rules-based ATS readiness score — not an AI judgment, and not any employer's actual screening system.",
                style: context.text.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
        Gap.section,
        const SectionHeader(title: "Score Breakdown"),
        CareerCard(
          variant: CareerCardVariant.outlined,
          child: Column(
            children: [for (final entry in analysis.scoreBreakdown.entries) _ScoreBar(componentKey: entry.key, component: entry.value)],
          ),
        ),
        if (analysis.strongMatches.isNotEmpty) ...[
          Gap.xl,
          _KeywordSection(
            title: "Strengths",
            subtitle: "Keywords and skills your CV already matches",
            icon: Icons.check_circle_outline_rounded,
            tone: AppTone.success,
            keywords: analysis.strongMatches,
          ),
        ],
        if (analysis.missingKeywords.isNotEmpty) ...[
          Gap.xl,
          _KeywordSection(
            title: "Missing Keywords",
            subtitle: "Add these where they're genuinely true for you",
            icon: Icons.error_outline_rounded,
            tone: AppTone.danger,
            keywords: analysis.missingKeywords,
          ),
        ],
        if (improvements.isNotEmpty) ...[
          Gap.xl,
          const SectionHeader(title: "Recommended Improvements"),
          CareerListGroup(
            children: [
              for (final item in improvements) CareerListRow(icon: Icons.tips_and_updates_outlined, tone: AppTone.warning, title: item),
            ],
          ),
        ],
        if (onAnalyzeAgain != null) ...[
          Gap.xl,
          AppOutlineButton(label: "Analyze Again", icon: Icons.refresh_rounded, onPressed: onAnalyzeAgain),
        ],
      ],
    );
  }
}

class _ScoreBar extends StatelessWidget {
  const _ScoreBar({required this.componentKey, required this.component});

  final String componentKey;
  final ScoreComponent component;

  @override
  Widget build(BuildContext context) {
    final label = atsComponentLabels[componentKey] ?? componentKey;
    final tone = component.score >= 75
        ? AppTone.success
        : component.score >= 50
            ? AppTone.warning
            : AppTone.danger;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(label, style: context.text.titleSmall)),
              Text("weight ${(component.weight * 100).round()}%", style: context.text.labelSmall),
              Gap.sm,
              Text("${component.score}%", style: context.text.titleSmall),
            ],
          ),
          Gap.xxs,
          CareerProgressBar(value: component.score / 100, tone: tone, semanticLabel: label),
        ],
      ),
    );
  }
}

class _KeywordSection extends StatelessWidget {
  const _KeywordSection({required this.title, required this.subtitle, required this.icon, required this.tone, required this.keywords});

  final String title;
  final String subtitle;
  final IconData icon;
  final AppTone tone;
  final List<String> keywords;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 20, color: tone.color(context)),
            Gap.xs,
            Expanded(child: Semantics(header: true, child: Text(title, style: context.text.titleLarge))),
          ],
        ),
        const SizedBox(height: 2),
        Text(subtitle, style: context.text.bodySmall),
        Gap.sm,
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [for (final keyword in keywords) TagChip(label: keyword, tone: tone)],
        ),
      ],
    );
  }
}
