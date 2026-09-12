import "../../../core/network/api_client.dart";
import "job_models.dart";

class JobFilters {
  const JobFilters({
    this.search,
    this.country,
    this.employmentType,
    this.workMode,
    this.experienceLevel,
    this.sort = "newest",
  });

  final String? search;
  final String? country;
  final String? employmentType;
  final String? workMode;
  final String? experienceLevel;
  final String sort;

  bool get isEmpty =>
      search == null && country == null && employmentType == null && workMode == null && experienceLevel == null;

  Map<String, dynamic> toQuery() => {
        if (search != null && search!.isNotEmpty) "search": search,
        if (country != null) "country": country,
        if (employmentType != null) "employment_type": employmentType,
        if (workMode != null) "work_mode": workMode,
        if (experienceLevel != null) "experience_level": experienceLevel,
        "sort": sort,
      };

  JobFilters copyWith({
    String? search,
    String? country,
    String? employmentType,
    String? workMode,
    String? experienceLevel,
    String? sort,
  }) =>
      JobFilters(
        search: search ?? this.search,
        country: country ?? this.country,
        employmentType: employmentType ?? this.employmentType,
        workMode: workMode ?? this.workMode,
        experienceLevel: experienceLevel ?? this.experienceLevel,
        sort: sort ?? this.sort,
      );
}

class JobRepository {
  JobRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<({List<JobCard> items, int total})> list({
    int page = 1,
    JobFilters filters = const JobFilters(),
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/jobs",
      queryParameters: {"page": page, "page_size": 20, ...filters.toQuery()},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => JobCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<JobDetail> getByIdOrSlug(String idOrSlug) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/jobs/$idOrSlug");
    return JobDetail.fromJson(response.data!);
  }

  Future<void> save(String jobId) => _apiClient.post("/jobs/$jobId/save");

  Future<void> unsave(String jobId) => _apiClient.delete("/jobs/$jobId/save");

  Future<({List<JobCard> items, int total})> listByCompany(String companyId, {int page = 1}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/jobs",
      queryParameters: {"page": page, "page_size": 20, "company_id": companyId},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => JobCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<({List<JobCard> items, int total})> listSaved({int page = 1}) async {
    final response =
        await _apiClient.get<Map<String, dynamic>>("/me/saved-jobs", queryParameters: {"page": page, "page_size": 20});
    final data = response.data!;
    final items = (data["items"] as List).map((e) => JobCard.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }
}
