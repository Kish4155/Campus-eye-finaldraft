class StatsModel {
  final int totalStudents;
  final int enrolledStudents;
  final int activeCameras;
  final int totalCameras;
  final int presentToday;
  final int attendanceRate;
  final int unresolvedAlerts;

  StatsModel({
    required this.totalStudents,
    required this.enrolledStudents,
    required this.activeCameras,
    required this.totalCameras,
    required this.presentToday,
    required this.attendanceRate,
    required this.unresolvedAlerts,
  });

  factory StatsModel.fromJson(Map<String, dynamic> json) {
    return StatsModel(
      totalStudents: json['total_students'] ?? 0,
      enrolledStudents: json['enrolled_students'] ?? 0,
      activeCameras: json['active_cameras'] ?? 0,
      totalCameras: json['total_cameras'] ?? 0,
      presentToday: json['present_today'] ?? 0,
      attendanceRate: json['attendance_rate'] ?? 0,
      unresolvedAlerts: json['unresolved_alerts'] ?? 0,
    );
  }

  factory StatsModel.empty() {
    return StatsModel(
      totalStudents: 0,
      enrolledStudents: 0,
      activeCameras: 0,
      totalCameras: 0,
      presentToday: 0,
      attendanceRate: 0,
      unresolvedAlerts: 0,
    );
  }
}
