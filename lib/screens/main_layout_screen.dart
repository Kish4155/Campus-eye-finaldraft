import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import 'dashboard_screen.dart';
import 'cameras_screen.dart';
import 'students_screen.dart';
import 'attendance_screen.dart';
import 'alerts_screen.dart';
import 'settings_screen.dart';

class MainLayoutScreen extends StatefulWidget {
  const MainLayoutScreen({super.key});

  @override
  State<MainLayoutScreen> createState() => _MainLayoutScreenState();
}

class _MainLayoutScreenState extends State<MainLayoutScreen> {
  int _selectedIndex = 0;

  final List<Widget> _pages = const [
    DashboardScreen(),
    CamerasScreen(),
    StudentsScreen(),
    AttendanceScreen(),
    AlertsScreen(),
    SettingsScreen(),
  ];

  final List<NavigationDestinationItem> _navItems = const [
    NavigationDestinationItem(icon: Icons.dashboard_outlined, activeIcon: Icons.dashboard, label: "Dashboard"),
    NavigationDestinationItem(icon: Icons.videocam_outlined, activeIcon: Icons.videocam, label: "Cameras"),
    NavigationDestinationItem(icon: Icons.people_outline, activeIcon: Icons.people, label: "Students"),
    NavigationDestinationItem(icon: Icons.assignment_outlined, activeIcon: Icons.assignment, label: "Attendance"),
    NavigationDestinationItem(icon: Icons.shield_outlined, activeIcon: Icons.shield, label: "Alerts"),
    NavigationDestinationItem(icon: Icons.settings_outlined, activeIcon: Icons.settings, label: "Settings"),
  ];

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppStateProvider>(context);
    final isDesktop = MediaQuery.of(context).size.width >= 900;

    return Scaffold(
      body: Row(
        children: [
          if (isDesktop) _buildSidebar(state),
          Expanded(
            child: Column(
              children: [
                _buildHeader(state, isDesktop),
                Expanded(child: _pages[_selectedIndex]),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: !isDesktop ? _buildBottomNavBar() : null,
    );
  }

  Widget _buildHeader(AppStateProvider state, bool isDesktop) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(bottom: BorderSide(color: AppTheme.cardBorder)),
      ),
      child: Row(
        children: [
          if (!isDesktop) ...[
            const Icon(Icons.shield_rounded, color: AppTheme.cyanPrimary, size: 26),
            const SizedBox(width: 10),
            const Text(
              "CAMPUS-EYE",
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textPrimary, letterSpacing: 1),
            ),
          ] else ...[
            Text(
              _navItems[_selectedIndex].label.toUpperCase(),
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: AppTheme.textPrimary, letterSpacing: 1.2),
            ),
          ],
          const Spacer(),
          // Server Connection Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: state.isConnected ? AppTheme.accentNeon.withOpacity(0.15) : AppTheme.alertRed.withOpacity(0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: state.isConnected ? AppTheme.accentNeon : AppTheme.alertRed),
            ),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: state.isConnected ? AppTheme.accentNeon : AppTheme.alertRed,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  state.isConnected ? "SYSTEM ONLINE" : "DISCONNECTED",
                  style: TextStyle(
                    color: state.isConnected ? AppTheme.accentNeon : AppTheme.alertRed,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          IconButton(
            onPressed: () => state.refreshAllData(),
            icon: const Icon(Icons.refresh_rounded, color: AppTheme.textSecondary),
            tooltip: "Refresh Server State",
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar(AppStateProvider state) {
    return Container(
      width: 250,
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(right: BorderSide(color: AppTheme.cardBorder)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Brand Header
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    gradient: AppTheme.primaryGradient,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.remove_red_eye_rounded, color: Colors.black, size: 22),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      "CAMPUS-EYE",
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.textPrimary, letterSpacing: 1.2),
                    ),
                    Text(
                      "AI Surveillance Hub",
                      style: TextStyle(fontSize: 11, color: AppTheme.cyanPrimary),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Divider(color: AppTheme.cardBorder, height: 1),
          const SizedBox(height: 16),
          // Navigation Links
          Expanded(
            child: ListView.builder(
              itemCount: _navItems.length,
              itemBuilder: (context, index) {
                final item = _navItems[index];
                final isSelected = _selectedIndex == index;

                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  child: Material(
                    color: isSelected ? AppTheme.cyanPrimary.withOpacity(0.15) : Colors.transparent,
                    borderRadius: BorderRadius.circular(12),
                    child: ListTile(
                      dense: true,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: isSelected ? const BorderSide(color: AppTheme.cyanPrimary, width: 1) : BorderSide.none,
                      ),
                      leading: Icon(
                        isSelected ? item.activeIcon : item.icon,
                        color: isSelected ? AppTheme.cyanPrimary : AppTheme.textSecondary,
                      ),
                      title: Text(
                        item.label,
                        style: TextStyle(
                          color: isSelected ? AppTheme.textPrimary : AppTheme.textSecondary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 14,
                        ),
                      ),
                      trailing: index == 4 && state.stats.unresolvedAlerts > 0
                          ? Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppTheme.alertRed,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                "${state.stats.unresolvedAlerts}",
                                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                              ),
                            )
                          : null,
                      onTap: () => setState(() => _selectedIndex = index),
                    ),
                  ),
                );
              },
            ),
          ),
          // Footer
          Padding(
            padding: const EdgeInsets.all(16),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.background,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Row(
                children: const [
                  Icon(Icons.memory, color: AppTheme.accentNeon, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "PyTorch MobileNetV3 Engine",
                      style: TextStyle(color: AppTheme.textMuted, fontSize: 11),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNavBar() {
    return NavigationBar(
      selectedIndex: _selectedIndex,
      onDestinationSelected: (index) => setState(() => _selectedIndex = index),
      backgroundColor: AppTheme.surface,
      indicatorColor: AppTheme.cyanPrimary.withOpacity(0.2),
      destinations: _navItems.map((item) {
        return NavigationDestination(
          icon: Icon(item.icon, color: AppTheme.textSecondary),
          selectedIcon: Icon(item.activeIcon, color: AppTheme.cyanPrimary),
          label: item.label,
        );
      }).toList(),
    );
  }
}

class NavigationDestinationItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  const NavigationDestinationItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
}
