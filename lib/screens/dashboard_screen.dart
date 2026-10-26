import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/mjpeg_viewer.dart';
import '../widgets/stat_card.dart';
import '../widgets/status_chip.dart';
import '../models/camera_model.dart';
import 'enrollment_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int? _selectedCameraId;

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppStateProvider>(context);
    final stats = state.stats;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Banner Alert if there are security alerts
          if (stats.unresolvedAlerts > 0) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                gradient: AppTheme.alertGradient,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      "${stats.unresolvedAlerts} Security Alert(s) Require Immediate Attention!",
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // KPI Stats Grid
          LayoutBuilder(
            builder: (context, constraints) {
              final crossAxisCount = constraints.maxWidth > 1000
                  ? 5
                  : constraints.maxWidth > 700
                      ? 3
                      : 2;
              return GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.3,
                children: [
                  StatCard(
                    title: "Active Students",
                    value: "${stats.totalStudents}",
                    subtext: "Enrolled: ${stats.enrolledStudents}",
                    icon: Icons.school_rounded,
                    iconColor: AppTheme.cyanPrimary,
                  ),
                  StatCard(
                    title: "Active Cameras",
                    value: "${stats.activeCameras}/${stats.totalCameras}",
                    subtext: "Live Feeds Online",
                    icon: Icons.videocam_rounded,
                    iconColor: AppTheme.accentNeon,
                  ),
                  StatCard(
                    title: "Present Today",
                    value: "${stats.presentToday}",
                    subtext: "Unique Facial Scans",
                    icon: Icons.how_to_reg_rounded,
                    iconColor: AppTheme.blueSecondary,
                  ),
                  StatCard(
                    title: "Attendance Rate",
                    value: "${stats.attendanceRate}%",
                    subtext: "Campus Coverage",
                    icon: Icons.pie_chart_rounded,
                    iconColor: AppTheme.purpleAccent,
                  ),
                  StatCard(
                    title: "Unresolved Alerts",
                    value: "${stats.unresolvedAlerts}",
                    subtext: "Security Events",
                    icon: Icons.notifications_active_rounded,
                    iconColor: AppTheme.alertRed,
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),

          // Main Layout Content: Quick Video Feed + Recent Activity
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 900) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 3, child: _buildLiveSurveillanceSection(state)),
                    const SizedBox(width: 20),
                    Expanded(flex: 2, child: _buildRecentActivitySection(context, state)),
                  ],
                );
              }
              return Column(
                children: [
                  _buildLiveSurveillanceSection(state),
                  const SizedBox(height: 20),
                  _buildRecentActivitySection(context, state),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildLiveSurveillanceSection(AppStateProvider state) {
    final allCameras = state.cameras;
    final activeCameras = allCameras.where((c) => c.status == "Active").toList();

    CameraModel? displayCam;
    if (_selectedCameraId != null) {
      displayCam = allCameras.where((c) => c.id == _selectedCameraId).firstOrNull;
    }
    displayCam ??= activeCameras.isNotEmpty ? activeCameras.first : allCameras.firstOrNull;

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(Icons.live_tv_rounded, color: AppTheme.cyanPrimary, size: 20),
                  SizedBox(width: 8),
                  Text(
                    "PRIMARY SECURITY FEED",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
                  ),
                ],
              ),
              if (allCameras.isNotEmpty)
                DropdownButton<int>(
                  value: displayCam?.id,
                  dropdownColor: AppTheme.surfaceLight,
                  style: const TextStyle(color: AppTheme.cyanPrimary, fontSize: 11, fontWeight: FontWeight.bold),
                  underline: const SizedBox.shrink(),
                  items: allCameras.map((c) {
                    return DropdownMenuItem<int>(
                      value: c.id,
                      child: Text("${c.name} (${c.status})"),
                    );
                  }).toList(),
                  onChanged: (newId) {
                    if (newId != null) setState(() => _selectedCameraId = newId);
                  },
                )
              else
                StatusChip.inactive(),
            ],
          ),
          const SizedBox(height: 16),
          if (displayCam != null && displayCam.status == "Active")
            MjpegViewer(cameraId: displayCam.id, height: 320)
          else if (displayCam != null)
            Container(
              height: 260,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.videocam_off_outlined, color: AppTheme.alertRed, size: 36),
                    const SizedBox(height: 8),
                    Text(
                      "${displayCam.name.toUpperCase()} IS INACTIVE",
                      style: const TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton(
                      onPressed: () => state.toggleCamera(displayCam!.id),
                      child: const Text("Activate Feed", style: TextStyle(color: AppTheme.accentNeon)),
                    ),
                  ],
                ),
              ),
            )
          else
            Container(
              height: 260,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: const Center(
                child: Text(
                  "No Cameras Configured In System",
                  style: TextStyle(color: AppTheme.textMuted, fontWeight: FontWeight.bold),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRecentActivitySection(BuildContext context, AppStateProvider state) {
    final recentLogs = state.attendance.take(5).toList();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(Icons.history_rounded, color: AppTheme.accentNeon, size: 20),
                  SizedBox(width: 8),
                  Text(
                    "RECENT FACIAL SCANS",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
                  ),
                ],
              ),
              TextButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const EnrollmentScreen()),
                  );
                },
                child: const Text("+ Enroll Student", style: TextStyle(color: AppTheme.cyanPrimary, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (recentLogs.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text("No facial attendance recorded yet today.", style: TextStyle(color: AppTheme.textMuted)),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: recentLogs.length,
              separatorBuilder: (context, index) => const Divider(color: AppTheme.cardBorder, height: 1),
              itemBuilder: (context, index) {
                final log = recentLogs[index];
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: AppTheme.surfaceLight,
                    backgroundImage: log.photoPath != null && log.photoPath!.isNotEmpty
                        ? NetworkImage(ApiConfig.fullImageUrl(log.photoPath))
                        : null,
                    child: log.photoPath == null || log.photoPath!.isEmpty
                        ? const Icon(Icons.person, color: AppTheme.textSecondary)
                        : null,
                  ),
                  title: Text(
                    log.studentName,
                    style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                  subtitle: Text(
                    "${log.rollNo} • ${log.cameraLocation}",
                    style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                  ),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.cyanPrimary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      "${(log.confidence * 100).toStringAsFixed(1)}%",
                      style: const TextStyle(color: AppTheme.cyanPrimary, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
