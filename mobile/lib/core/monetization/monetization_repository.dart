import "../network/api_client.dart";
import "monetization_models.dart";

class MonetizationRepository {
  MonetizationRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<MonetizationConfig> getConfig() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/monetization/config");
    return MonetizationConfig.fromJson(response.data!);
  }

  Future<Entitlement> getEntitlement() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/monetization/entitlement");
    return Entitlement.fromJson(response.data!);
  }

  /// `referenceId` must be a fresh, unique value per ad-watch attempt (a UUID) — the backend uses
  /// it as an idempotency key so a duplicated reward callback can never grant a reward twice
  /// (spec §17).
  Future<RewardUnlock> claimReward({required RewardType rewardType, required String referenceId}) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/monetization/rewards/claim",
      data: {"reward_type": rewardType.wireValue, "reference_id": referenceId},
    );
    return RewardUnlock.fromJson(response.data!);
  }
}
