import "../../../core/network/api_client.dart";
import "scholarship_models.dart";

class ScholarshipFilters {
  const ScholarshipFilters({this.search, this.country, this.degreeLevel, this.fundingType});

  final String? search;
  final String? country;
  final String? degreeLevel;
  final String? fundingType;

  Map<String, dynamic> toQuery() => {
        if (search != null && search!.isNotEmpty) "search": search,
        if (country != null) "country": country,
        if (degreeLevel != null) "degree_level": degreeLevel,
        if (fundingType != null) "funding_type": fundingType,
      };

  ScholarshipFilters copyWith({String? search, String? country, String? degreeLevel, String? fundingType}) =>
      ScholarshipFilters(
        search: search ?? this.search,
        country: country ?? this.country,
        degreeLevel: degreeLevel ?? this.degreeLevel,
        fundingType: fundingType ?? this.fundingType,
      );
}

class ScholarshipRepository {
  ScholarshipRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<({List<ScholarshipCard> items, int total})> list({
    int page = 1,
    ScholarshipFilters filters = const ScholarshipFilters(),
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/scholarships",
      queryParameters: {"page": page, "page_size": 20, ...filters.toQuery()},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => ScholarshipCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<ScholarshipDetail> getByIdOrSlug(String idOrSlug) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/scholarships/$idOrSlug");
    return ScholarshipDetail.fromJson(response.data!);
  }

  Future<void> save(String scholarshipId) => _apiClient.post("/scholarships/$scholarshipId/save");

  Future<void> unsave(String scholarshipId) => _apiClient.delete("/scholarships/$scholarshipId/save");

  Future<({List<ScholarshipCard> items, int total})> listSaved({int page = 1}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/me/saved-scholarships",
      queryParameters: {"page": page, "page_size": 20},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => ScholarshipCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }
}
