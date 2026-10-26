class ApiConfig {
  static String baseUrl = "http://127.0.0.1:5050";

  static void setBaseUrl(String url) {
    if (url.endsWith('/')) {
      baseUrl = url.substring(0, url.length - 1);
    } else {
      baseUrl = url;
    }
  }

  // Endpoints
  static String get statsUrl => "$baseUrl/api/stats";
  static String get camerasUrl => "$baseUrl/api/cameras";
  static String get detectCamerasUrl => "$baseUrl/api/cameras/detect";
  static String get studentsUrl => "$baseUrl/api/students";
  static String get enrollStudentUrl => "$baseUrl/api/students/enroll";
  static String get attendanceUrl => "$baseUrl/api/attendance";
  static String get exportAttendanceUrl => "$baseUrl/api/attendance/export";
  static String get alertsUrl => "$baseUrl/api/alerts";

  static String videoFeedUrl(int cameraId) => "$baseUrl/video_feed/$cameraId";
  static String videoFrameUrl(int cameraId) => "$baseUrl/video_frame/$cameraId";
  static String toggleCameraUrl(int cameraId) => "$baseUrl/api/cameras/$cameraId/toggle";
  static String cameraModeUrl(int cameraId) => "$baseUrl/api/cameras/$cameraId/mode";
  static String deleteCameraUrl(int cameraId) => "$baseUrl/api/cameras/$cameraId";
  
  static String toggleStudentUrl(int studentId) => "$baseUrl/api/students/$studentId/toggle";
  static String deleteStudentUrl(int studentId) => "$baseUrl/api/students/$studentId";
  static String resolveAlertUrl(int alertId) => "$baseUrl/api/alerts/$alertId/resolve";

  static String fullImageUrl(String? path) {
    if (path == null || path.isEmpty) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    return "$baseUrl$path";
  }
}
