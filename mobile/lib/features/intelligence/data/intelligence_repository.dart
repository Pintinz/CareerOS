import "../../../core/network/api_client.dart";
import "intelligence_models.dart";

class IntelligenceRepository {
  IntelligenceRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<({List<IntelligenceCard> items, int total})> list({
    int page = 1,
    String? search,
    String? category,
    bool followedOnly = false,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/intelligence",
      queryParameters: {
        "page": page,
        "page_size": 20,
        if (search != null && search.isNotEmpty) "search": search,
        if (category != null) "category": category,
        if (followedOnly) "followed_only": true,
      },
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => IntelligenceCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<IntelligenceDetail> getByIdOrSlug(String idOrSlug) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/intelligence/$idOrSlug");
    return IntelligenceDetail.fromJson(response.data!);
  }

  Future<({List<IntelligenceCard> items, int total})> listByCompany(String companyId, {int page = 1}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/intelligence",
      queryParameters: {"page": page, "page_size": 20, "company_id": companyId},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => IntelligenceCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }
}
