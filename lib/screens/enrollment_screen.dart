import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/mjpeg_viewer.dart';

class EnrollmentScreen extends StatefulWidget {
  const EnrollmentScreen({super.key});

  @override
  State<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends State<EnrollmentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _rollCtrl = TextEditingController();
  String _department = "Computer Science";
  Uint8List? _selectedBytes;
  String? _selectedBase64;
  bool _isSubmitting = false;
  bool _isCapturingLive = false;
  String? _statusMessage;
  bool _isSuccess = false;
  bool _useLiveCamera = false;
  int? _selectedCameraId;

  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? photo = await _picker.pickImage(source: source, imageQuality: 90);
      if (photo != null) {
        final bytes = await photo.readAsBytes();
        setState(() {
          _selectedBytes = bytes;
          _selectedBase64 = base64Encode(bytes);
          _useLiveCamera = false;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error selecting image: $e")),
      );
    }
  }

  Future<void> _captureLiveFrame(int cameraId) async {
    setState(() => _isCapturingLive = true);
    try {
      final uri = Uri.parse(ApiConfig.videoFrameUrl(cameraId));
      final resp = await http.get(uri).timeout(const Duration(seconds: 4));
      if (resp.statusCode == 200 && resp.bodyBytes.isNotEmpty) {
        setState(() {
          _selectedBytes = resp.bodyBytes;
          _selectedBase64 = base64Encode(resp.bodyBytes);
          _isCapturingLive = false;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              backgroundColor: AppTheme.accentNeon,
              content: Text("✓ Live Camera Frame Captured! Ready to submit.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        setState(() => _isCapturingLive = false);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Camera frame is initializing. Please wait a moment and try again.")),
          );
        }
      }
    } catch (e) {
      setState(() => _isCapturingLive = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Capture error: $e")),
        );
      }
    }
  }

  Future<void> _submitEnrollment() async {
    if (!_formKey.currentState!.validate()) return;

    if (!_useLiveCamera && _selectedBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please take a photo, upload a file, or capture from a live camera.")),
      );
      return;
    }

    if (_useLiveCamera && _selectedCameraId == null && _selectedBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please select an active camera for live capture.")),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
      _statusMessage = null;
    });

    Map<String, dynamic> res;

    // If user captured a snapshot from the live camera or uploaded a file
    if (_selectedBytes != null) {
      res = await ApiService.enrollStudent(
        name: _nameCtrl.text.trim(),
        rollNo: _rollCtrl.text.trim().toUpperCase(),
        department: _department,
        status: "Active",
        imageBytes: _selectedBytes,
        imageBase64: _selectedBase64,
      );
    } else if (_useLiveCamera && _selectedCameraId != null) {
      res = await ApiService.enrollStudentFromCamera(
        name: _nameCtrl.text.trim(),
        rollNo: _rollCtrl.text.trim().toUpperCase(),
        department: _department,
        status: "Active",
        cameraId: _selectedCameraId!,
      );
    } else {
      res = {"success": false, "error": "No image data available."};
    }

    setState(() {
      _isSubmitting = false;
      _isSuccess = res['success'] == true;
      _statusMessage = res['message'] ?? res['error'] ?? "Unknown response from server";
    });

    if (_isSuccess) {
      if (mounted) {
        Provider.of<AppStateProvider>(context, listen: false).refreshAllData();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppStateProvider>(context);
    final activeCameras = state.cameras.where((c) => c.status == 'Active').toList();

    int? effectiveCameraId;
    if (activeCameras.isNotEmpty) {
      if (_selectedCameraId != null && activeCameras.any((c) => c.id == _selectedCameraId)) {
        effectiveCameraId = _selectedCameraId;
      } else {
        effectiveCameraId = activeCameras.first.id;
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Student Face Enrollment"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 700),
            child: GlassCard(
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "PYTORCH DEEP FEATURE EMBEDDING REGISTRATION",
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.cyanPrimary, letterSpacing: 1),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      "Enroll Student Profile",
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 20),

                    // Source Selection Toggle
                    Row(
                      children: [
                        Expanded(
                          child: _SourceToggleButton(
                            icon: Icons.photo_library,
                            label: "Photo / Upload",
                            isActive: !_useLiveCamera,
                            onTap: () => setState(() => _useLiveCamera = false),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _SourceToggleButton(
                            icon: Icons.videocam,
                            label: "Live Camera Capture",
                            isActive: _useLiveCamera,
                            onTap: activeCameras.isEmpty
                                ? null
                                : () => setState(() {
                                    _useLiveCamera = true;
                                    _selectedCameraId = effectiveCameraId;
                                  }),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    // Photo Upload Area OR Live Camera Feed
                    if (!_useLiveCamera) ...[
                      Center(
                        child: Column(
                          children: [
                            Container(
                              width: 160,
                              height: 160,
                              decoration: BoxDecoration(
                                color: AppTheme.surfaceLight,
                                shape: BoxShape.circle,
                                border: Border.all(color: AppTheme.cyanPrimary, width: 2),
                                image: _selectedBytes != null
                                    ? DecorationImage(image: MemoryImage(_selectedBytes!), fit: BoxFit.cover)
                                    : null,
                              ),
                              child: _selectedBytes == null
                                  ? const Icon(Icons.face, size: 70, color: AppTheme.textMuted)
                                  : null,
                            ),
                            const SizedBox(height: 12),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                OutlinedButton.icon(
                                  onPressed: () => _pickImage(ImageSource.camera),
                                  icon: const Icon(Icons.camera_alt, size: 16),
                                  label: const Text("Capture Camera"),
                                ),
                                const SizedBox(width: 12),
                                OutlinedButton.icon(
                                  onPressed: () => _pickImage(ImageSource.gallery),
                                  icon: const Icon(Icons.photo_library, size: 16),
                                  label: const Text("Upload File"),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ] else ...[
                      // Camera selector dropdown
                      DropdownButtonFormField<int>(
                        value: effectiveCameraId,
                        decoration: const InputDecoration(labelText: "Select Active Camera"),
                        dropdownColor: AppTheme.surfaceLight,
                        items: activeCameras.map((cam) {
                          return DropdownMenuItem<int>(
                            value: cam.id,
                            child: Text("${cam.name} (${cam.location})"),
                          );
                        }).toList(),
                        onChanged: (val) {
                          setState(() {
                            _selectedCameraId = val;
                            _selectedBytes = null;
                            _selectedBase64 = null;
                          });
                        },
                      ),
                      const SizedBox(height: 12),

                      // Live feed preview
                      if (effectiveCameraId != null) ...[
                        ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: SizedBox(
                            height: 280,
                            child: MjpegViewer(
                              cameraId: effectiveCameraId,
                              height: 280,
                              fit: BoxFit.contain,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Center(
                          child: ElevatedButton.icon(
                            onPressed: _isCapturingLive ? null : () => _captureLiveFrame(effectiveCameraId!),
                            icon: _isCapturingLive
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                                : const Icon(Icons.camera_rounded, color: Colors.black),
                            label: Text(
                              _selectedBytes != null ? "📸 Retake Live Snapshot" : "📸 Capture Photo From Live Camera",
                              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.accentNeon,
                              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                            ),
                          ),
                        ),
                        if (_selectedBytes != null) ...[
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: AppTheme.accentNeon.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.accentNeon),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(20),
                                  child: Image.memory(_selectedBytes!, width: 44, height: 44, fit: BoxFit.cover),
                                ),
                                const SizedBox(width: 12),
                                const Expanded(
                                  child: Text(
                                    "✓ Live photo captured! Click 'Complete Student Enrollment' below.",
                                    style: TextStyle(color: AppTheme.accentNeon, fontSize: 12, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ] else
                        Container(
                          height: 200,
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Center(
                            child: Text("No active cameras available. Please add/enable a camera first.", style: TextStyle(color: AppTheme.textMuted)),
                          ),
                        ),
                    ],
                    const SizedBox(height: 24),

                    // Inputs
                    TextFormField(
                      controller: _nameCtrl,
                      decoration: const InputDecoration(labelText: "Full Student Name *"),
                      validator: (val) => val == null || val.isEmpty ? "Name is required" : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _rollCtrl,
                      decoration: const InputDecoration(labelText: "Roll Number / Student ID *"),
                      validator: (val) => val == null || val.isEmpty ? "Roll Number is required" : null,
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _department,
                      decoration: const InputDecoration(labelText: "Department"),
                      dropdownColor: AppTheme.surfaceLight,
                      items: const [
                        DropdownMenuItem(value: "Computer Science", child: Text("Computer Science")),
                        DropdownMenuItem(value: "Electrical Eng", child: Text("Electrical Eng")),
                        DropdownMenuItem(value: "Mechanical Eng", child: Text("Mechanical Eng")),
                        DropdownMenuItem(value: "Business Admin", child: Text("Business Admin")),
                      ],
                      onChanged: (val) => setState(() => _department = val!),
                    ),
                    const SizedBox(height: 24),

                    // Status Message
                    if (_statusMessage != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _isSuccess ? AppTheme.accentNeon.withOpacity(0.15) : AppTheme.alertRed.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: _isSuccess ? AppTheme.accentNeon : AppTheme.alertRed),
                        ),
                        child: Row(
                          children: [
                            Icon(_isSuccess ? Icons.check_circle : Icons.error,
                                color: _isSuccess ? AppTheme.accentNeon : AppTheme.alertRed),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _statusMessage!,
                                style: TextStyle(
                                  color: _isSuccess ? AppTheme.accentNeon : AppTheme.alertRed,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                    ],

                    // Submit Button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isSubmitting ? null : _submitEnrollment,
                        icon: _isSubmitting
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2))
                            : Icon(_useLiveCamera ? Icons.videocam : Icons.face, size: 18),
                        label: Text(
                          _useLiveCamera
                              ? "Capture Face from Live Feed & Enroll"
                              : "Extract Facial Features & Enroll",
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SourceToggleButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback? onTap;

  const _SourceToggleButton({
    required this.icon,
    required this.label,
    required this.isActive,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: isActive ? AppTheme.cyanPrimary.withOpacity(0.15) : AppTheme.surfaceLight,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isActive ? AppTheme.cyanPrimary : AppTheme.cardBorder,
            width: isActive ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: isActive ? AppTheme.cyanPrimary : AppTheme.textMuted, size: 28),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                color: isActive ? AppTheme.cyanPrimary : AppTheme.textMuted,
                fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                fontSize: 12,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
