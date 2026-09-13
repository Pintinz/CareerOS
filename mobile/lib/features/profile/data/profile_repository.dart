import "../../../core/network/api_client.dart";

class CurrentUser {
  const CurrentUser({required this.id, required this.email, required this.isVerified});

  final String id;
  final String email;
  final bool isVerified;

  factory CurrentUser.fromJson(Map<String, dynamic> json) => CurrentUser(
        id: json["id"] as String,
        email: json["email"] as String,
        isVerified: json["is_verified"] as bool,
      );
}

class UserProfile {
  const UserProfile({
    this.fullName,
    this.profilePictureUrl,
    this.professionalTitle,
    this.location,
    this.yearsOfExperience,
    this.highestEducation,
    this.fieldOfStudy,
  });

  final String? fullName;
  final String? profilePictureUrl;
  final String? professionalTitle;
  final String? location;
  final int? yearsOfExperience;
  final String? highestEducation;
  final String? fieldOfStudy;

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        fullName: json["full_name"] as String?,
        profilePictureUrl: json["profile_picture_url"] as String?,
        professionalTitle: json["professional_title"] as String?,
        location: json["location"] as String?,
        yearsOfExperience: json["years_of_experience"] as int?,
        highestEducation: json["highest_education"] as String?,
        fieldOfStudy: json["field_of_study"] as String?,
      );
}

class ProfileRepository {
  ProfileRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<CurrentUser> getCurrentUser() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/auth/me");
    return CurrentUser.fromJson(response.data!);
  }

  Future<UserProfile> getProfile() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/profile");
    return UserProfile.fromJson(response.data!);
  }

  /// Sends only the keys present in [fields] (API semantics: omitted = unchanged, null = cleared).
  Future<UserProfile> updateProfileFields(Map<String, Object?> fields) async {
    final response = await _apiClient.put<Map<String, dynamic>>("/profile", data: fields);
    return UserProfile.fromJson(response.data!);
  }

  Future<UserProfile> updateProfile({String? fullName, String? location}) => updateProfileFields({
        if (fullName != null) "full_name": fullName,
        if (location != null) "location": location,
      });
}
