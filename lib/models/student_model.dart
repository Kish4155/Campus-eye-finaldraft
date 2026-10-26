class StudentModel {
  final int id;
  final String name;
  final String rollNo;
  final String department;
  final String status;
  final String? photoPath;
  final bool faceEnrolled;
  final String? createdAt;

  StudentModel({
    required this.id,
    required this.name,
    required this.rollNo,
    required this.department,
    required this.status,
    this.photoPath,
    required this.faceEnrolled,
    this.createdAt,
  });

  factory StudentModel.fromJson(Map<String, dynamic> json) {
    return StudentModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      rollNo: json['roll_no'] ?? '',
      department: json['department'] ?? 'General',
      status: json['status'] ?? 'Active',
      photoPath: json['photo_path'],
      faceEnrolled: (json['face_enrolled'] == 1 || json['face_enrolled'] == true),
      createdAt: json['created_at'],
    );
  }
}
