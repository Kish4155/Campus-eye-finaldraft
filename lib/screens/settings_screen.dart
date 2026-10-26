import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _urlCtrl.text = ApiConfig.baseUrl;
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppStateProvider>(context);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "APPLICATION & SERVER CONFIGURATION",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 20),

                // Backend Host Settings Card
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.dns, color: AppTheme.cyanPrimary),
                          SizedBox(width: 10),
                          Text("Flask Backend Endpoint", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        "Set the IP address of the machine running python run_app.py (e.g. http://127.0.0.1:5050 or http://192.168.x.x:5050 for mobile testing).",
                        style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _urlCtrl,
                        decoration: const InputDecoration(
                          labelText: "Server Base URL",
                          prefixIcon: Icon(Icons.link, color: AppTheme.cyanPrimary),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          ElevatedButton.icon(
                            onPressed: () {
                              state.setBaseUrl(_urlCtrl.text.trim());
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text("Backend URL updated successfully!")),
                              );
                            },
                            icon: const Icon(Icons.save, size: 16),
                            label: const Text("Save & Reconnect"),
                          ),
                          const SizedBox(width: 12),
                          OutlinedButton.icon(
                            onPressed: () => state.refreshAllData(),
                            icon: const Icon(Icons.sync, size: 16),
                            label: const Text("Ping Server"),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: AppTheme.cyanPrimary,
                              side: const BorderSide(color: AppTheme.cyanPrimary),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // About & System Info
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.info_outline, color: AppTheme.accentNeon),
                          SizedBox(width: 10),
                          Text("CAMPUS-EYE Cross-Platform Hub", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text("Framework Version"),
                        subtitle: Text("Flutter Cross-Platform 3.x (iOS, Android, Windows, Web, macOS)"),
                      ),
                      const ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text("AI Facial Engine"),
                        subtitle: Text("PyTorch MobileNetV3 + Cosine Similarity Matcher (576-dim Embeddings)"),
                      ),
                      const ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text("Active Database"),
                        subtitle: Text("SQLite DB (campus_eye.db)"),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
