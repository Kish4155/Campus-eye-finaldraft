import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/mjpeg_viewer.dart';
import '../widgets/status_chip.dart';

class CamerasScreen extends StatelessWidget {
  const CamerasScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppStateProvider>(context);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Bar & Actions
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "SURVEILLANCE CAMERAS",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Text(
                      "${state.cameras.where((c) => c.status == 'Active').length} / ${state.cameras.length} Feeds Online",
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ),
                Row(
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _showDetectCamerasDialog(context),
                      icon: const Icon(Icons.search, size: 18),
                      label: const Text("Scan Hardware"),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.cyanPrimary,
                        side: const BorderSide(color: AppTheme.cyanPrimary),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: () => _showAddCameraDialog(context, state),
                      icon: const Icon(Icons.add, size: 18),
                      label: const Text("Add Camera"),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Cameras Grid
            if (state.cameras.isEmpty)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text("No surveillance cameras configured yet.", style: TextStyle(color: AppTheme.textMuted)),
                ),
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final crossAxisCount = constraints.maxWidth > 1100 ? 3 : constraints.maxWidth > 700 ? 2 : 1;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: state.cameras.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                      childAspectRatio: 1.15,
                    ),
                    itemBuilder: (context, index) {
                      final cam = state.cameras[index];
                      return GlassCard(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Stream Header
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        cam.name,
                                        style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary, fontSize: 14),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      Text(
                                        "${cam.location} • ${cam.sourceType.toUpperCase()}",
                                        style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                      ),
                                    ],
                                  ),
                                ),
                                cam.status == "Active" ? StatusChip.active() : StatusChip.inactive(),
                              ],
                            ),
                            const SizedBox(height: 10),

                            // Video Player / MJPEG Frame
                            Expanded(
                              child: cam.status == "Active"
                                  ? MjpegViewer(cameraId: cam.id)
                                  : Container(
                                      decoration: BoxDecoration(
                                        color: Colors.black,
                                        borderRadius: BorderRadius.circular(10),
                                        border: Border.all(color: AppTheme.cardBorder),
                                      ),
                                      child: const Center(
                                        child: Text("CAMERA INACTIVE", style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
                                      ),
                                    ),
                            ),
                            const SizedBox(height: 10),

                            // Controls Row
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                // Mode selector dropdown
                                DropdownButton<String>(
                                  value: const [
                                    "all",
                                    "attendance_only",
                                    "id_card",
                                    "grooming",
                                    "shoes",
                                    "crowding",
                                    "intruders",
                                    "disabled"
                                  ].contains(cam.detectionMode)
                                      ? cam.detectionMode
                                      : "all",
                                  dropdownColor: AppTheme.surfaceLight,
                                  style: const TextStyle(color: AppTheme.cyanPrimary, fontSize: 11, fontWeight: FontWeight.bold),
                                  underline: const SizedBox.shrink(),
                                  items: const [
                                    DropdownMenuItem(value: "all", child: Text("All AI Suites")),
                                    DropdownMenuItem(value: "attendance_only", child: Text("Attendance Only")),
                                    DropdownMenuItem(value: "id_card", child: Text("ID Card Audit")),
                                    DropdownMenuItem(value: "grooming", child: Text("Haircut / Grooming")),
                                    DropdownMenuItem(value: "shoes", child: Text("Footwear Audit")),
                                    DropdownMenuItem(value: "crowding", child: Text("Crowd Density")),
                                    DropdownMenuItem(value: "intruders", child: Text("Intruders Only")),
                                    DropdownMenuItem(value: "disabled", child: Text("Disabled")),
                                  ],
                                  onChanged: (newMode) {
                                    if (newMode != null) {
                                      state.setCameraMode(cam.id, newMode);
                                    }
                                  },
                                ),
                                Row(
                                  children: [
                                    IconButton(
                                      icon: Icon(
                                        cam.status == "Active" ? Icons.power_settings_new : Icons.play_arrow,
                                        color: cam.status == "Active" ? AppTheme.alertRed : AppTheme.accentNeon,
                                        size: 20,
                                      ),
                                      onPressed: () => state.toggleCamera(cam.id),
                                      tooltip: cam.status == "Active" ? "Turn Off" : "Turn On",
                                    ),
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline, color: AppTheme.textMuted, size: 20),
                                      onPressed: () => state.deleteCamera(cam.id),
                                      tooltip: "Delete Camera",
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  void _showAddCameraDialog(BuildContext context, AppStateProvider state) {
    final nameCtrl = TextEditingController(text: "New Camera");
    final locationCtrl = TextEditingController(text: "Main Entrance");
    final urlCtrl = TextEditingController(text: "0");
    String sourceType = "device";
    String mode = "all";

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Allot New Camera Feed", style: TextStyle(fontWeight: FontWeight.bold)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: "Camera Name"),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: sourceType,
                decoration: const InputDecoration(labelText: "Source Type"),
                dropdownColor: AppTheme.surfaceLight,
                items: const [
                  DropdownMenuItem(value: "device", child: Text("Webcam Device")),
                  DropdownMenuItem(value: "ip", child: Text("RTSP / IP Stream")),
                  DropdownMenuItem(value: "simulated", child: Text("Simulated Video")),
                ],
                onChanged: (val) => sourceType = val ?? "device",
              ),
              const SizedBox(height: 12),
              TextField(
                controller: urlCtrl,
                decoration: const InputDecoration(labelText: "Device Index / RTSP URL"),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: locationCtrl,
                decoration: const InputDecoration(labelText: "Location"),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          ElevatedButton(
            onPressed: () async {
              final success = await ApiService.addCamera(
                name: nameCtrl.text,
                sourceType: sourceType,
                sourceUrl: urlCtrl.text,
                location: locationCtrl.text,
                detectionMode: mode,
                capacityLimit: 10,
              );
              if (success) {
                state.fetchCameras();
                state.fetchStats();
                if (context.mounted) Navigator.pop(context);
              }
            },
            child: const Text("Add Camera"),
          ),
        ],
      ),
    );
  }

  void _showDetectCamerasDialog(BuildContext context) async {
    showDialog(
      context: context,
      builder: (context) => const AlertDialog(
        content: Padding(
          padding: EdgeInsets.all(20),
          child: Row(
            children: [
              CircularProgressIndicator(color: AppTheme.cyanPrimary),
              SizedBox(width: 20),
              Text("Scanning host hardware webcams..."),
            ],
          ),
        ),
      ),
    );

    final devices = await ApiService.detectCameras();
    if (context.mounted) {
      Navigator.pop(context); // Close loading dialog
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text("Detected Hardware Cameras"),
          content: devices.isEmpty
              ? const Text("No USB/Hardware webcams detected.")
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: devices.map((d) {
                    return ListTile(
                      leading: const Icon(Icons.videocam, color: AppTheme.cyanPrimary),
                      title: Text(d['name'] ?? 'Device'),
                      subtitle: Text("Index: ${d['index']}"),
                    );
                  }).toList(),
                ),
          actions: [
            ElevatedButton(onPressed: () => Navigator.pop(context), child: const Text("Close")),
          ],
        ),
      );
    }
  }
}
