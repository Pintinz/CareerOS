import "../../../core/network/api_client.dart";
import "company_models.dart";

class CompanyRepository {
  CompanyRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<({List<Company> items, int total})> list({int page = 1, String? search}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/companies",
      queryParameters: {"page": page, "page_size": 20, if (search != null && search.isNotEmpty) "search": search},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => Company.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<Company> getByIdOrSlug(String idOrSlug) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/companies/$idOrSlug");
    return Company.fromJson(response.data!);
  }

  Future<void> follow(String companyId) => _apiClient.post("/companies/$companyId/follow");

  Future<void> unfollow(String companyId) => _apiClient.delete("/companies/$companyId/follow");

  Future<List<Company>> listFollowed() async {
    final response = await _apiClient.get<List<dynamic>>("/me/followed-companies");
    return response.data!.map((e) => Company.fromJson(e as Map<String, dynamic>)).toList();
  }
}
