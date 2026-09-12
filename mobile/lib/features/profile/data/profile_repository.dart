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
  const UserProfile({this.fullName, this.professionalTitle, this.location});

  final String? fullName;
  final String? professionalTitle;
  final String? location;

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        fullName: json["full_name"] as String?,
        professionalTitle: json["professional_title"] as String?,
        location: json["location"] as String?,
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

  Future<UserProfile> updateProfile({String? fullName, String? location}) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/profile",
      data: {if (fullName != null) "full_name": fullName, if (location != null) "location": location},
    );
    return UserProfile.fromJson(response.data!);
  }
}
