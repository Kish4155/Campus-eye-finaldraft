import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../theme/app_theme.dart';

class MjpegViewer extends StatefulWidget {
  final int cameraId;
  final double? height;
  final BoxFit fit;

  const MjpegViewer({
    super.key,
    required this.cameraId,
    this.height,
    this.fit = BoxFit.cover,
  });

  @override
  State<MjpegViewer> createState() => _MjpegViewerState();
}

class _MjpegViewerState extends State<MjpegViewer> {
  final http.Client _client = http.Client();
  Uint8List? _frameBytes;
  bool _hasError = false;
  bool _isLoading = true;
  bool _isStreaming = false;

  @override
  void initState() {
    super.initState();
    _startStream();
  }

  @override
  void didUpdateWidget(covariant MjpegViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cameraId != widget.cameraId) {
      _stopStream();
      setState(() {
        _frameBytes = null;
        _isLoading = true;
        _hasError = false;
      });
      _startStream();
    }
  }

  @override
  void dispose() {
    _stopStream();
    _client.close();
    super.dispose();
  }

  void _startStream() {
    _isStreaming = true;
    _fetchLoop();
  }

  void _stopStream() {
    _isStreaming = false;
  }

  int _consecutiveErrors = 0;

  Future<void> _fetchLoop() async {
    while (mounted && _isStreaming) {
      try {
        final uri = Uri.parse(ApiConfig.videoFrameUrl(widget.cameraId));
        final response = await _client.get(uri).timeout(const Duration(milliseconds: 2500));
        
        if (!mounted || !_isStreaming) break;

        if (response.statusCode == 200 && response.bodyBytes.isNotEmpty) {
          _consecutiveErrors = 0;
          setState(() {
            _frameBytes = response.bodyBytes;
            _hasError = false;
            _isLoading = false;
          });
        } else if (response.statusCode == 204) {
          // Camera active but frame warming up
          _consecutiveErrors = 0;
          if (_isLoading && _frameBytes == null) {
            // Keep loading indicator
          }
        } else {
          _consecutiveErrors++;
          if (_consecutiveErrors >= 6 && _frameBytes == null) {
            setState(() {
              _hasError = true;
              _isLoading = false;
            });
          }
        }
      } catch (e) {
        if (!mounted || !_isStreaming) break;
        _consecutiveErrors++;
        if (_consecutiveErrors >= 6 && _frameBytes == null) {
          setState(() {
            _hasError = true;
            _isLoading = false;
          });
        }
      }
      
      // Target smooth 20-25 FPS refresh
      await Future.delayed(const Duration(milliseconds: 50));
    }
  }

  void _retry() {
    setState(() {
      _hasError = false;
      _isLoading = true;
      _frameBytes = null;
      _consecutiveErrors = 0;
    });
    _startStream();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: widget.height,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          if (_frameBytes != null)
            Image.memory(
              _frameBytes!,
              fit: widget.fit,
              width: double.infinity,
              height: widget.height ?? double.infinity,
              gaplessPlayback: true,
              errorBuilder: (context, error, stackTrace) {
                return const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(color: AppTheme.cyanPrimary, strokeWidth: 2),
                      SizedBox(height: 8),
                      Text("SYNCING FRAME...", style: TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                    ],
                  ),
                );
              },
            )
          else if (_hasError)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.videocam_off_outlined, color: AppTheme.alertRed, size: 42),
                  const SizedBox(height: 8),
                  const Text(
                    "CAMERA FEED OFFLINE",
                    style: TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _retry,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text("Reconnect"),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.cyanPrimary,
                      side: const BorderSide(color: AppTheme.cyanPrimary),
                    ),
                  )
                ],
              ),
            )
          else
            const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: AppTheme.cyanPrimary),
                  SizedBox(height: 12),
                  Text(
                    "INITIALIZING AI STREAM...",
                    style: TextStyle(color: AppTheme.textMuted, fontSize: 11, letterSpacing: 1),
                  ),
                ],
              ),
            ),

          // Live HUD Status Badge
          Positioned(
            top: 10,
            left: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.75),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: (_hasError ? AppTheme.alertRed : AppTheme.cyanPrimary).withOpacity(0.4),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _hasError ? AppTheme.alertRed : AppTheme.accentNeon,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _hasError ? "OFFLINE" : (_frameBytes != null ? "LIVE STREAM" : "CONNECTING"),
                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1),
                  ),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }
}
