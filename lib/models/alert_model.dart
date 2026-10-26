class AlertModel {
  final int id;
  final int cameraId;
  final String alertType;
  final String description;
  final String timestamp;
  final String? snapshotPath;
  final bool isResolved;
  final String cameraName;
  final String cameraLocation;

  AlertModel({
    required this.id,
    required this.cameraId,
    required this.alertType,
    required this.description,
    required this.timestamp,
    this.snapshotPath,
    required this.isResolved,
    required this.cameraName,
    required this.cameraLocation,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id'] ?? 0,
      cameraId: json['camera_id'] ?? 0,
      alertType: json['alert_type'] ?? 'Security Event',
      description: json['description'] ?? '',
      timestamp: json['timestamp'] ?? '',
      snapshotPath: json['snapshot_path'],
      isResolved: (json['is_resolved'] == 1 || json['is_resolved'] == true),
      cameraName: json['camera_name'] ?? 'Camera',
      cameraLocation: json['camera_location'] ?? 'Campus Zone',
    );
  }
}
