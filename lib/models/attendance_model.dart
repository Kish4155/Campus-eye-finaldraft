class AttendanceRecord {
  final int id;
  final String timestamp;
  final double confidence;
  final String method;
  final String status;
  final String studentName;
  final String rollNo;
  final String department;
  final String? photoPath;
  final String cameraName;
  final String cameraLocation;

  AttendanceRecord({
    required this.id,
    required this.timestamp,
    required this.confidence,
    required this.method,
    required this.status,
    required this.studentName,
    required this.rollNo,
    required this.department,
    this.photoPath,
    required this.cameraName,
    required this.cameraLocation,
  });

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) {
    return AttendanceRecord(
      id: json['id'] ?? 0,
      timestamp: json['timestamp'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      method: json['method'] ?? 'AI Scan',
      status: json['status'] ?? 'Present',
      studentName: json['student_name'] ?? 'Unknown',
      rollNo: json['roll_no'] ?? '',
      department: json['department'] ?? '',
      photoPath: json['photo_path'],
      cameraName: json['camera_name'] ?? 'Camera',
      cameraLocation: json['camera_location'] ?? 'Campus Zone',
    );
  }
}
