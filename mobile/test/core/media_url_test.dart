import "package:careeros/core/widgets/network_image.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  test("local backend media URLs follow the API host used by the device", () {
    expect(
      resolveMediaUrl("http://localhost:8000/uploads/logo.png", apiBaseUrl: "http://10.0.2.2:8000/api/v1"),
      "http://10.0.2.2:8000/uploads/logo.png",
    );
    expect(
      resolveMediaUrl("http://127.0.0.1:8000/uploads/logo.png", apiBaseUrl: "http://192.168.1.20:8000/api/v1"),
      "http://192.168.1.20:8000/uploads/logo.png",
    );
  });

  test("deployment and same-host URLs are unchanged", () {
    expect(
      resolveMediaUrl("https://cdn.careeros.app/uploads/logo.png", apiBaseUrl: "http://10.0.2.2:8000/api/v1"),
      "https://cdn.careeros.app/uploads/logo.png",
    );
    expect(
      resolveMediaUrl("http://localhost:8000/uploads/logo.png", apiBaseUrl: "http://localhost:8000/api/v1"),
      "http://localhost:8000/uploads/logo.png",
    );
  });
}
