import 'dart:async';
import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../models/camera_model.dart';
import '../models/student_model.dart';
import '../models/attendance_model.dart';
import '../models/alert_model.dart';
import '../models/stats_model.dart';
import '../services/api_service.dart';

class AppStateProvider extends ChangeNotifier {
  StatsModel _stats = StatsModel.empty();
  List<CameraModel> _cameras = [];
  List<StudentModel> _students = [];
  List<AttendanceRecord> _attendance = [];
  List<AlertModel> _alerts = [];
  
  bool _isLoading = false;
  bool _isConnected = false;
  String _selectedDepartment = "All Departments";
  String _searchQuery = "";
  Timer? _pollingTimer;

  // Getters
  StatsModel get stats => _stats;
  List<CameraModel> get cameras => _cameras;
  List<StudentModel> get students => _filteredStudents;
  List<AttendanceRecord> get attendance => _attendance;
  List<AlertModel> get alerts => _alerts;
  bool get isLoading => _isLoading;
  bool get isConnected => _isConnected;
  String get selectedDepartment => _selectedDepartment;
  String get searchQuery => _searchQuery;

  AppStateProvider() {
    init();
  }

  void init() {
    refreshAllData();
    // Auto-refresh stats every 4 seconds
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      fetchStats();
      fetchCameras();
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  void setBaseUrl(String newUrl) {
    ApiConfig.setBaseUrl(newUrl);
    refreshAllData();
  }

  void setSelectedDepartment(String dept) {
    _selectedDepartment = dept;
    fetchAttendance();
    notifyListeners();
  }

  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  List<StudentModel> get _filteredStudents {
    if (_searchQuery.isEmpty && _selectedDepartment == "All Departments") {
      return _students;
    }
    return _students.where((s) {
      final matchesSearch = s.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          s.rollNo.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesDept = _selectedDepartment == "All Departments" || s.department == _selectedDepartment;
      return matchesSearch && matchesDept;
    }).toList();
  }

  Future<void> refreshAllData() async {
    _isLoading = true;
    notifyListeners();

    await Future.wait([
      fetchStats(),
      fetchCameras(),
      fetchStudents(),
      fetchAttendance(),
      fetchAlerts(),
    ]);

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchStats() async {
    final s = await ApiService.getStats();
    if (s != null) {
      _stats = s;
      _isConnected = true;
    } else {
      _isConnected = false;
    }
    notifyListeners();
  }

  Future<void> fetchCameras() async {
    final list = await ApiService.getCameras();
    _cameras = list;
    notifyListeners();
  }

  Future<void> fetchStudents() async {
    final list = await ApiService.getStudents();
    _students = list;
    notifyListeners();
  }

  Future<void> fetchAttendance() async {
    final list = await ApiService.getAttendance(department: _selectedDepartment);
    _attendance = list;
    notifyListeners();
  }

  Future<void> fetchAlerts() async {
    final list = await ApiService.getAlerts();
    _alerts = list;
    notifyListeners();
  }

  // Camera Mutations
  Future<bool> toggleCamera(int id) async {
    final success = await ApiService.toggleCamera(id);
    if (success) fetchCameras();
    return success;
  }

  Future<bool> setCameraMode(int id, String mode) async {
    final success = await ApiService.setCameraMode(id, mode);
    if (success) fetchCameras();
    return success;
  }

  Future<bool> deleteCamera(int id) async {
    final success = await ApiService.deleteCamera(id);
    if (success) fetchCameras();
    return success;
  }

  // Student Mutations
  Future<bool> toggleStudent(int id) async {
    final success = await ApiService.toggleStudent(id);
    if (success) fetchStudents();
    return success;
  }

  Future<bool> deleteStudent(int id) async {
    final success = await ApiService.deleteStudent(id);
    if (success) fetchStudents();
    return success;
  }

  // Alert Mutation
  Future<bool> resolveAlert(int id) async {
    final success = await ApiService.resolveAlert(id);
    if (success) {
      fetchAlerts();
      fetchStats();
    }
    return success;
  }
}
