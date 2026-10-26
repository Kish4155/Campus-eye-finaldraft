import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/status_chip.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

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
            // Top Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "SECURITY ALERTS & INTRUSION AUDIT",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Text(
                      "${state.alerts.where((a) => !a.isResolved).length} Active Unresolved Alerts",
                      style: const TextStyle(fontSize: 12, color: AppTheme.alertRed, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, color: AppTheme.cyanPrimary),
                  onPressed: () => state.fetchAlerts(),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Alerts Grid/List
            if (state.alerts.isEmpty)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text("No security threat alerts logged.", style: TextStyle(color: AppTheme.textMuted)),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: state.alerts.length,
                separatorBuilder: (context, index) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final alert = state.alerts[index];
                  final snapshotUrl = alert.snapshotPath != null ? ApiConfig.fullImageUrl(alert.snapshotPath) : null;

                  return GlassCard(
                    padding: const EdgeInsets.all(16),
                    borderColor: alert.isResolved ? AppTheme.cardBorder : AppTheme.alertRed.withOpacity(0.5),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Snapshot image or Icon
                        Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: alert.isResolved ? AppTheme.cardBorder : AppTheme.alertRed),
                            image: snapshotUrl != null && snapshotUrl.isNotEmpty
                                ? DecorationImage(image: NetworkImage(snapshotUrl), fit: BoxFit.cover)
                                : null,
                          ),
                          child: snapshotUrl == null || snapshotUrl.isEmpty
                              ? Icon(Icons.security, color: alert.isResolved ? AppTheme.textMuted : AppTheme.alertRed, size: 36)
                              : null,
                        ),
                        const SizedBox(width: 16),

                        // Details
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    alert.alertType.toUpperCase(),
                                    style: TextStyle(
                                      color: alert.isResolved ? AppTheme.textMuted : AppTheme.alertRed,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 13,
                                      letterSpacing: 1,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  alert.isResolved ? StatusChip.inactive() : StatusChip.alert(),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                alert.description,
                                style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w500, fontSize: 14),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                "Location: ${alert.cameraName} (${alert.cameraLocation}) • ${alert.timestamp}",
                                style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                              ),
                            ],
                          ),
                        ),

                        // Actions
                        if (!alert.isResolved)
                          ElevatedButton.icon(
                            onPressed: () => state.resolveAlert(alert.id),
                            icon: const Icon(Icons.check, size: 16),
                            label: const Text("Resolve"),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.accentNeon,
                              foregroundColor: Colors.black,
                            ),
                          ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
