class CompanySummary {
  const CompanySummary({required this.id, required this.name, required this.slug, this.logoUrl});

  final String id;
  final String name;
  final String slug;
  final String? logoUrl;

  factory CompanySummary.fromJson(Map<String, dynamic> json) => CompanySummary(
        id: json["id"] as String,
        name: json["name"] as String,
        slug: json["slug"] as String,
        logoUrl: json["logo_url"] as String?,
      );
}

class Company {
  const Company({
    required this.id,
    required this.name,
    required this.slug,
    this.logoUrl,
    this.bannerUrl,
    this.websiteUrl,
    this.careerUrl,
    this.industry,
    this.headquarters,
    this.country,
    this.description,
    required this.isVerified,
    required this.isActive,
    this.isDemo = false,
    this.isFollowing = false,
  });

  final String id;
  final String name;
  final String slug;
  final String? logoUrl;
  final String? bannerUrl;
  final String? websiteUrl;
  final String? careerUrl;
  final String? industry;
  final String? headquarters;
  final String? country;
  final String? description;
  final bool isVerified;
  final bool isActive;
  final bool isDemo;
  final bool isFollowing;

  factory Company.fromJson(Map<String, dynamic> json) => Company(
        id: json["id"] as String,
        name: json["name"] as String,
        slug: json["slug"] as String,
        logoUrl: json["logo_url"] as String?,
        bannerUrl: json["banner_url"] as String?,
        websiteUrl: json["website_url"] as String?,
        careerUrl: json["career_url"] as String?,
        industry: json["industry"] as String?,
        headquarters: json["headquarters"] as String?,
        country: json["country"] as String?,
        description: json["description"] as String?,
        isVerified: json["is_verified"] as bool? ?? false,
        isActive: json["is_active"] as bool? ?? true,
        isDemo: json["is_demo"] as bool? ?? false,
        isFollowing: json["is_following"] as bool? ?? false,
      );
}
