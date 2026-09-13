import "package:flutter/material.dart";
import "package:url_launcher/url_launcher.dart";

const _allowedSchemes = {"http", "https"};

/// Opens an external URL (job/scholarship application links, company websites, news sources).
/// Never impersonates the destination — always hands off to the system browser (spec §14).
///
/// Only http/https are allowed: this content ultimately comes from admin-entered fields
/// (job/scholarship application URLs, company websites, intelligence source links) with no
/// scheme validation on the backend, so a scheme like `javascript:`/`data:`/`file:` must be
/// rejected here rather than trusted (Phase 9.5 security audit finding).
Future<void> openExternalUrl(BuildContext context, String? url) async {
  if (url == null || url.isEmpty) return;

  final uri = Uri.tryParse(url);
  if (uri == null || !_allowedSchemes.contains(uri.scheme.toLowerCase())) {
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
