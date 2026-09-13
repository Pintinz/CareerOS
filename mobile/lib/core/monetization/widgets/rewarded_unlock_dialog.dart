import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../ad_placement.dart";
import "../monetization_models.dart";
import "../monetization_providers.dart";

/// Spec §15's exact flow, as a reusable dialog: "Daily free limit reached — Want another
/// session? [Watch Ad & Unlock] / [Come Back Tomorrow]". Returns true only if a reward was
/// actually granted (the SDK's real earned-reward callback fired AND the server-side idempotent
/// claim succeeded) — the caller should proceed only on `true`. Never locks basic functionality:
/// the user can always dismiss and simply not get the extra session (spec §14).
Future<bool> showRewardedUnlockDialog(
  BuildContext context, {
  required String title,
  required String message,
  required AdPlacement placement,
  required RewardType rewardType,
}) async {
  final result = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (context) => _RewardedUnlockDialog(title: title, message: message, placement: placement, rewardType: rewardType),
  );
  return result ?? false;
}

class _RewardedUnlockDialog extends ConsumerStatefulWidget {
  const _RewardedUnlockDialog({
    required this.title,
    required this.message,
    required this.placement,
    required this.rewardType,
  });

  final String title;
  final String message;
  final AdPlacement placement;
  final RewardType rewardType;

  @override
  ConsumerState<_RewardedUnlockDialog> createState() => _RewardedUnlockDialogState();
}

class _RewardedUnlockDialogState extends ConsumerState<_RewardedUnlockDialog> {
  bool _watching = false;
  String? _error;

  Future<void> _watchAd() async {
    setState(() {
      _watching = true;
      _error = null;
    });
    try {
      final granted = await ref
          .read(adServiceProvider)
          .showRewarded(placement: widget.placement, rewardType: widget.rewardType);
      if (!mounted) return;
      if (granted) {
        Navigator.of(context).pop(true);
      } else {
        setState(() {
          _watching = false;
          _error = "The ad couldn't be completed, so nothing was unlocked. You can try again or come back later.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _watching = false;
        _error = "Something went wrong loading the ad. You can try again or come back later.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(widget.message),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: _watching ? null : () => Navigator.of(context).pop(false),
          child: const Text("Come Back Tomorrow"),
        ),
        FilledButton(
          onPressed: _watching ? null : _watchAd,
          child: _watching
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text("Watch Ad & Unlock"),
        ),
      ],
    );
  }
}
