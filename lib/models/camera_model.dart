class CameraLiveStats {
  final String status;
  final double fps;
  final int facesCount;

  CameraLiveStats({
    required this.status,
    required this.fps,
    required this.facesCount,
  });

  factory CameraLiveStats.fromJson(Map<String, dynamic> json) {
    return CameraLiveStats(
      status: json['status'] ?? 'Offline',
      fps: (json['fps'] ?? 0).toDouble(),
      facesCount: json['faces_count'] ?? 0,
    );
  }
}

class CameraModel {
  final int id;
  final String name;
  final String sourceType;
  final String sourceUrl;
  final String location;
  final String status;
  final String detectionMode;
  final int capacityLimit;
  final CameraLiveStats liveStats;

  CameraModel({
    required this.id,
    required this.name,
    required this.sourceType,
    required this.sourceUrl,
    required this.location,
    required this.status,
    required this.detectionMode,
    required this.capacityLimit,
    required this.liveStats,
  });

  factory CameraModel.fromJson(Map<String, dynamic> json) {
    return CameraModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? 'Camera',
      sourceType: json['source_type'] ?? 'device',
      sourceUrl: json['source_url'] ?? '0',
      location: json['location'] ?? 'Campus',
      status: json['status'] ?? 'Inactive',
      detectionMode: json['detection_mode'] ?? 'all',
      capacityLimit: json['capacity_limit'] ?? 10,
      liveStats: json['live_stats'] != null
          ? CameraLiveStats.fromJson(json['live_stats'])
          : CameraLiveStats(status: 'Offline', fps: 0, facesCount: 0),
    );
  }
}
