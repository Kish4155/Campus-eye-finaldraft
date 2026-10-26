import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/camera_model.dart';
import '../models/student_model.dart';
import '../models/attendance_model.dart';
import '../models/alert_model.dart';
import '../models/stats_model.dart';

class ApiService {
  // Fetch System Stats
  static Future<StatsModel?> getStats() async {
    try {
      final response = await http.get(Uri.parse(ApiConfig.statsUrl)).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          return StatsModel.fromJson(data);
        }
      }
    } catch (e) {
      print("ApiService getStats error: $e");
    }
    return null;
  }

  // Fetch Cameras
  static Future<List<CameraModel>> getCameras() async {
    try {
      final response = await http.get(Uri.parse(ApiConfig.camerasUrl)).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['cameras'] != null) {
          final List items = data['cameras'];
          return items.map((c) => CameraModel.fromJson(c)).toList();
        }
      }
    } catch (e) {
      print("ApiService getCameras error: $e");
    }
    return [];
  }

  // Detect Available Webcams on Host
  static Future<List<dynamic>> detectCameras() async {
    try {
      final response = await http.get(Uri.parse(ApiConfig.detectCamerasUrl));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          return data['devices'] ?? [];
        }
      }
    } catch (e) {
      print("ApiService detectCameras error: $e");
    }
    return [];
  }

  // Add New Camera
  static Future<bool> addCamera({
    required String name,
    required String sourceType,
    required String sourceUrl,
    required String location,
    required String detectionMode,
    required int capacityLimit,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(ApiConfig.camerasUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "name": name,
          "source_type": sourceType,
          "source_url": sourceUrl,
          "location": location,
          "detection_mode": detectionMode,
          "capacity_limit": capacityLimit,
        }),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService addCamera error: $e");
    }
    return false;
  }

  // Toggle Camera
  static Future<bool> toggleCamera(int cameraId) async {
    try {
      final response = await http.post(Uri.parse(ApiConfig.toggleCameraUrl(cameraId)));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService toggleCamera error: $e");
    }
    return false;
  }

  // Set Camera Mode
  static Future<bool> setCameraMode(int cameraId, String mode) async {
    try {
      final response = await http.post(
        Uri.parse(ApiConfig.cameraModeUrl(cameraId)),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"detection_mode": mode}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService setCameraMode error: $e");
    }
    return false;
  }

  // Delete Camera
  static Future<bool> deleteCamera(int cameraId) async {
    try {
      final response = await http.delete(Uri.parse(ApiConfig.deleteCameraUrl(cameraId)));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService deleteCamera error: $e");
    }
    return false;
  }

  // Fetch Students
  static Future<List<StudentModel>> getStudents() async {
    try {
      final response = await http.get(Uri.parse(ApiConfig.studentsUrl)).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['students'] != null) {
          final List items = data['students'];
          return items.map((s) => StudentModel.fromJson(s)).toList();
        }
      }
    } catch (e) {
      print("ApiService getStudents error: $e");
    }
    return [];
  }

  // Enroll Student Face (Multipart / Base64 / Bytes)
  static Future<Map<String, dynamic>> enrollStudent({
    required String name,
    required String rollNo,
    required String department,
    required String status,
    String? imageBase64,
    Uint8List? imageBytes,
    dynamic imageFile,
  }) async {
    try {
      final uri = Uri.parse(ApiConfig.enrollStudentUrl);
      
      // 1. If base64 provided, use fast JSON POST
      if (imageBase64 != null && imageBase64.isNotEmpty) {
        final response = await http.post(
          uri,
          headers: {"Content-Type": "application/json"},
          body: jsonEncode({
            "name": name,
            "roll_no": rollNo,
            "department": department,
            "status": status,
            "image_base64": imageBase64,
          }),
        ).timeout(const Duration(seconds: 15));
        if (response.statusCode == 200 || response.statusCode == 400) {
          return jsonDecode(response.body);
        }
      }

      // 2. Otherwise use Multipart for Bytes or File
      final request = http.MultipartRequest("POST", uri);
      request.fields['name'] = name;
      request.fields['roll_no'] = rollNo;
      request.fields['department'] = department;
      request.fields['status'] = status;

      if (imageBytes != null && imageBytes.isNotEmpty) {
        request.files.add(
          http.MultipartFile.fromBytes('photo', imageBytes, filename: 'enroll_${rollNo}.jpg')
        );
      } else if (imageFile != null) {
        try {
          request.files.add(await http.MultipartFile.fromPath('photo', imageFile.path));
        } catch (_) {}
      }

      final streamedResponse = await request.send().timeout(const Duration(seconds: 15));
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode == 200 || response.statusCode == 400) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print("ApiService enrollStudent error: $e");
      return {"success": false, "error": e.toString()};
    }
    return {"success": false, "error": "Server error"};
  }

  // Enroll Student Face directly from a Live Camera Feed
  static Future<Map<String, dynamic>> enrollStudentFromCamera({
    required String name,
    required String rollNo,
    required String department,
    required String status,
    required int cameraId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(ApiConfig.enrollStudentUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "name": name,
          "roll_no": rollNo,
          "department": department,
          "status": status,
          "camera_id": cameraId,
        }),
      ).timeout(const Duration(seconds: 15));
      if (response.statusCode == 200 || response.statusCode == 400) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print("ApiService enrollStudentFromCamera error: $e");
      return {"success": false, "error": e.toString()};
    }
    return {"success": false, "error": "Server error"};
  }

  // Toggle Student Status
  static Future<bool> toggleStudent(int studentId) async {
    try {
      final response = await http.post(Uri.parse(ApiConfig.toggleStudentUrl(studentId)));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService toggleStudent error: $e");
    }
    return false;
  }

  // Delete Student
  static Future<bool> deleteStudent(int studentId) async {
    try {
      final response = await http.delete(Uri.parse(ApiConfig.deleteStudentUrl(studentId)));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService deleteStudent error: $e");
    }
    return false;
  }

  // Fetch Attendance Records
  static Future<List<AttendanceRecord>> getAttendance({String? department, int limit = 100}) async {
    try {
      String url = "${ApiConfig.attendanceUrl}?limit=$limit";
      if (department != null && department.isNotEmpty && department != "All Departments") {
        url += "&department=${Uri.encodeComponent(department)}";
      }
      final response = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['records'] != null) {
          final List items = data['records'];
          return items.map((r) => AttendanceRecord.fromJson(r)).toList();
        }
      }
    } catch (e) {
      print("ApiService getAttendance error: $e");
    }
    return [];
  }

  // Fetch Security Alerts
  static Future<List<AlertModel>> getAlerts() async {
    try {
      final response = await http.get(Uri.parse(ApiConfig.alertsUrl)).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['alerts'] != null) {
          final List items = data['alerts'];
          return items.map((a) => AlertModel.fromJson(a)).toList();
        }
      }
    } catch (e) {
      print("ApiService getAlerts error: $e");
    }
    return [];
  }

  // Resolve Alert
  static Future<bool> resolveAlert(int alertId) async {
    try {
      final response = await http.post(Uri.parse(ApiConfig.resolveAlertUrl(alertId)));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      }
    } catch (e) {
      print("ApiService resolveAlert error: $e");
    }
    return false;
  }
}
