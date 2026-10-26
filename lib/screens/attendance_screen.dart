import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/status_chip.dart';

class AttendanceScreen extends StatelessWidget {
  const AttendanceScreen({super.key});

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
            // Header Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "ATTENDANCE LEDGER & AUDIT TRAIL",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Text(
                      "${state.attendance.length} Total Verification Logs",
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    // Open CSV Export URL in browser or inform user
                    final exportUrl = ApiConfig.exportAttendanceUrl;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text("Export URL: $exportUrl")),
                    );
                  },
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text("Export CSV Ledger"),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.accentNeon,
                    foregroundColor: Colors.black,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Department Filter Bar
            GlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  const Icon(Icons.filter_list, color: AppTheme.cyanPrimary),
                  const SizedBox(width: 12),
                  const Text("Filter Department: ", style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(width: 12),
                  DropdownButton<String>(
                    value: const [
                      "All Departments",
                      "Computer Science",
                      "Electrical Eng",
                      "Mechanical Eng",
                      "Business Admin"
                    ].contains(state.selectedDepartment)
                        ? state.selectedDepartment
                        : "All Departments",
                    dropdownColor: AppTheme.surfaceLight,
                    underline: const SizedBox.shrink(),
                    style: const TextStyle(color: AppTheme.cyanPrimary, fontWeight: FontWeight.bold),
                    items: const [
                      DropdownMenuItem(value: "All Departments", child: Text("All Departments")),
                      DropdownMenuItem(value: "Computer Science", child: Text("Computer Science")),
                      DropdownMenuItem(value: "Electrical Eng", child: Text("Electrical Eng")),
                      DropdownMenuItem(value: "Mechanical Eng", child: Text("Mechanical Eng")),
                      DropdownMenuItem(value: "Business Admin", child: Text("Business Admin")),
                    ],
                    onChanged: (val) {
                      if (val != null) state.setSelectedDepartment(val);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Logs Table
            if (state.attendance.isEmpty)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text("No attendance records found.", style: TextStyle(color: AppTheme.textMuted)),
                ),
              )
            else
              GlassCard(
                padding: EdgeInsets.zero,
                child: ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: state.attendance.length,
                  separatorBuilder: (context, index) => const Divider(color: AppTheme.cardBorder, height: 1),
                  itemBuilder: (context, index) {
                    final log = state.attendance[index];
                    final photoUrl = log.photoPath != null ? ApiConfig.fullImageUrl(log.photoPath) : null;
                    final confPercent = (log.confidence * 100).toStringAsFixed(1);

                    return ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      leading: CircleAvatar(
                        radius: 20,
                        backgroundColor: AppTheme.surfaceLight,
                        backgroundImage: photoUrl != null ? NetworkImage(photoUrl) : null,
                        child: photoUrl == null ? const Icon(Icons.person, color: AppTheme.textSecondary) : null,
                      ),
                      title: Row(
                        children: [
                          Text(log.studentName, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                          const SizedBox(width: 8),
                          Text("(${log.rollNo})", style: const TextStyle(color: AppTheme.blueSecondary, fontSize: 12)),
                        ],
                      ),
                      subtitle: Text(
                        "${log.department} • ${log.cameraName} (${log.cameraLocation}) • ${log.timestamp}",
                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Confidence meter
                          Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text("$confPercent% Match", style: const TextStyle(color: AppTheme.cyanPrimary, fontWeight: FontWeight.bold, fontSize: 12)),
                              Text(log.method, style: const TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                            ],
                          ),
                          const SizedBox(width: 16),
                          StatusChip.present(),
                        ],
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
