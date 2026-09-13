import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../data/ats_models.dart";

class AtsResultView extends StatelessWidget {
  const AtsResultView({super.key, required this.analysis, this.onAnalyzeAgain});

  final AtsAnalysis analysis;
  final VoidCallback? onAnalyzeAgain;

  Color get _scoreColor {
    if (analysis.overallScore >= 75) return AppColors.success;
    if (analysis.overallScore >= 50) return AppColors.warning;
    return AppColors.danger;
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Column(
              children: [
                SizedBox(
                  width: 120,
                  height: 120,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      SizedBox(
                        width: 120,
                        height: 120,
                        child: CircularProgressIndicator(
                          value: analysis.overallScore / 100,
                          strokeWidth: 10,
                          backgroundColor: AppColors.muted.withValues(alpha: 0.15),
                          valueColor: AlwaysStoppedAnimation(_scoreColor),
                        ),
                      ),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            "${analysis.overallScore}",
                            style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: _scoreColor),
                          ),
                          const Text("Job Match", style: TextStyle(fontSize: 12, color: AppColors.muted)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  "Rules-based ATS readiness score — not an AI judgment.",
                  style: TextStyle(fontSize: 12, color: AppColors.muted),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Text("Score Breakdown", style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          for (final entry in analysis.scoreBreakdown.entries) _ScoreBar(componentKey: entry.key, component: entry.value),
          if (analysis.strongMatches.isNotEmpty) ...[
            const SizedBox(height: 20),
            _KeywordSection(
              title: "Strong Matches",
              icon: Icons.check_circle_outline,
              color: AppColors.success,
              keywords: analysis.strongMatches,
            ),
          ],
          if (analysis.missingKeywords.isNotEmpty) ...[
            const SizedBox(height: 16),
            _KeywordSection(
              title: "Missing Critical Keywords",
              icon: Icons.error_outline,
              color: AppColors.danger,
              keywords: analysis.missingKeywords,
            ),
          ],
          if (analysis.formattingIssues.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text("Formatting Problems", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            for (final issue in analysis.formattingIssues)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.warning_amber_rounded, size: 16, color: AppColors.warning),
                    const SizedBox(width: 8),
                    Expanded(child: Text(issue)),
                  ],
                ),
              ),
          ],
          if (analysis.missingMetricsNote != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.warning.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(analysis.missingMetricsNote!, style: const TextStyle(fontSize: 13)),
            ),
          ],
          if (onAnalyzeAgain != null) ...[
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(onPressed: onAnalyzeAgain, child: const Text("Analyze Again")),
            ),
          ],
        ],
      ),
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "$label (${(component.weight * 100).round()}%)",
                style: const TextStyle(fontSize: 13, color: AppColors.muted),
              ),
              Text("${component.score}%", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: component.score / 100,
              minHeight: 6,
              backgroundColor: AppColors.muted.withValues(alpha: 0.15),
              valueColor: const AlwaysStoppedAnimation(AppColors.blue),
            ),
          ),
        ],
      ),
    );
  }
}

class _KeywordSection extends StatelessWidget {
  const _KeywordSection({required this.title, required this.icon, required this.color, required this.keywords});

  final String title;
  final IconData icon;
  final Color color;
  final List<String> keywords;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: color),
            const SizedBox(width: 6),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final keyword in keywords)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
                child: Text(keyword, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
              ),
          ],
        ),
      ],
    );
  }
}
