import "package:flutter/material.dart";
import "package:url_launcher/url_launcher.dart";

/// Opens an external URL (job/scholarship application links, company websites, news sources).
/// Never impersonates the destination — always hands off to the system browser (spec §14).
Future<void> openExternalUrl(BuildContext context, String? url) async {
  if (url == null || url.isEmpty) return;

  final uri = Uri.tryParse(url);
  if (uri == null) {
    _showError(context, "This link looks invalid.");
    return;
  }

  final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!launched && context.mounted) {
    _showError(context, "Couldn't open this link.");
  }
}

void _showError(BuildContext context, String message) {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}
