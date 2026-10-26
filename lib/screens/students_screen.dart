import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/status_chip.dart';
import 'enrollment_screen.dart';

class StudentsScreen extends StatelessWidget {
  const StudentsScreen({super.key});

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
            // Top Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "STUDENT ROSTER & FACIAL ENROLLMENT",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Text(
                      "${state.students.length} Total Enrolled Students",
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const EnrollmentScreen()),
                    );
                  },
                  icon: const Icon(Icons.person_add, size: 18),
                  label: const Text("Enroll Face & Student"),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Filter Bar
            GlassCard(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      decoration: const InputDecoration(
                        hintText: "Search student name or roll number...",
                        prefixIcon: Icon(Icons.search, color: AppTheme.textMuted),
                      ),
                      onChanged: (val) => state.setSearchQuery(val),
                    ),
                  ),
                  const SizedBox(width: 16),
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
                    style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold),
                    underline: const SizedBox.shrink(),
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

            // Students List Table
            if (state.students.isEmpty)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text("No students found matching filter criteria.", style: TextStyle(color: AppTheme.textMuted)),
                ),
              )
            else
              GlassCard(
                padding: EdgeInsets.zero,
                child: ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: state.students.length,
                  separatorBuilder: (context, index) => const Divider(color: AppTheme.cardBorder, height: 1),
                  itemBuilder: (context, index) {
                    final student = state.students[index];
                    final photoUrl = student.photoPath != null ? ApiConfig.fullImageUrl(student.photoPath) : null;

                    return ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      leading: CircleAvatar(
                        radius: 22,
                        backgroundColor: AppTheme.surfaceLight,
                        backgroundImage: photoUrl != null ? NetworkImage(photoUrl) : null,
                        child: photoUrl == null ? const Icon(Icons.person, color: AppTheme.textSecondary) : null,
                      ),
                      title: Row(
                        children: [
                          Text(
                            student.name,
                            style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                          ),
                          const SizedBox(width: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.blueSecondary.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              student.rollNo,
                              style: const TextStyle(color: AppTheme.blueSecondary, fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      subtitle: Text(
                        "${student.department} • Registered: ${student.createdAt ?? 'N/A'}",
                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (student.faceEnrolled)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              margin: const EdgeInsets.only(right: 12),
                              decoration: BoxDecoration(
                                color: AppTheme.accentNeon.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: AppTheme.accentNeon),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.face, color: AppTheme.accentNeon, size: 14),
                                  SizedBox(width: 4),
                                  Text("Face Enrolled", style: TextStyle(color: AppTheme.accentNeon, fontSize: 10, fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ),
                          student.status == "Active" ? StatusChip.active() : StatusChip.inactive(),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: Icon(
                              student.status == "Active" ? Icons.toggle_on : Icons.toggle_off,
                              color: student.status == "Active" ? AppTheme.accentNeon : AppTheme.textMuted,
                              size: 26,
                            ),
                            onPressed: () => state.toggleStudent(student.id),
                            tooltip: "Toggle Status",
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: AppTheme.textMuted, size: 20),
                            onPressed: () => state.deleteStudent(student.id),
                            tooltip: "Delete Student",
                          ),
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
