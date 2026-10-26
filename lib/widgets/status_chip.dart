import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  final String label;
  final Color color;
  final bool isGlowing;

  const StatusChip({
    super.key,
    required this.label,
    required this.color,
    this.isGlowing = false,
  });

  factory StatusChip.active() => const StatusChip(label: "Active", color: AppTheme.accentNeon, isGlowing: true);
  factory StatusChip.inactive() => const StatusChip(label: "Inactive", color: AppTheme.textMuted);
  factory StatusChip.present() => const StatusChip(label: "Present", color: AppTheme.cyanPrimary);
  factory StatusChip.alert() => const StatusChip(label: "Unresolved", color: AppTheme.alertRed, isGlowing: true);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.5)),
        boxShadow: isGlowing
            ? [
                BoxShadow(
                  color: color.withOpacity(0.3),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
