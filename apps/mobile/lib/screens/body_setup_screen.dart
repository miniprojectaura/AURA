/// Body Setup Screen — Camera/gallery photo capture → AI body analysis → measurements display.
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

class BodySetupScreen extends ConsumerStatefulWidget {
  const BodySetupScreen({super.key});
  @override
  ConsumerState<BodySetupScreen> createState() => _BodySetupScreenState();
}

class _BodySetupScreenState extends ConsumerState<BodySetupScreen> {
  final ImagePicker _picker = ImagePicker();
  bool _isAnalyzing = false;
  Map<String, dynamic>? _analysisResult;
  String? _error;
  Uint8List? _photoBytes;
  int _currentStep = 0; // 0=capture, 1=analyzing, 2=results

  Future<void> _pickPhoto(ImageSource source) async {
    try {
      final XFile? image = await _picker.pickImage(
        source: source,
        maxWidth: 1200,
        maxHeight: 1600,
        imageQuality: 85,
      );
      if (image == null) return;

      final bytes = await image.readAsBytes();
      setState(() {
        _photoBytes = bytes;
        _currentStep = 1;
        _isAnalyzing = true;
        _error = null;
      });

      await _analyzePhoto(bytes, image.name);
    } catch (e) {
      setState(() {
        _error = 'Failed to pick image: $e';
        _currentStep = 0;
      });
    }
  }

  Future<void> _analyzePhoto(Uint8List bytes, String filename) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.loadSavedToken();
      final result = await api.analyzeBodyPhoto(bytes.toList(), filename);

      setState(() {
        _analysisResult = result;
        _isAnalyzing = false;
        _currentStep = 2;
      });
    } catch (e) {
      setState(() {
        _error = 'Analysis failed: $e';
        _isAnalyzing = false;
        _currentStep = 0;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.gradientSurface),
        child: SafeArea(
          child: Column(
            children: [
              // App bar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new, color: AppColors.primaryDark),
                      onPressed: () => context.go('/home'),
                    ),
                    const Expanded(
                      child: Text('Body Profile Setup', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.primaryDark), textAlign: TextAlign.center),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),

              // Step indicator
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Row(
                  children: [
                    _StepDot(label: 'Capture', isActive: _currentStep >= 0, isDone: _currentStep > 0),
                    Expanded(child: Container(height: 2, color: _currentStep > 0 ? AppColors.primary : AppColors.border)),
                    _StepDot(label: 'Analyze', isActive: _currentStep >= 1, isDone: _currentStep > 1),
                    Expanded(child: Container(height: 2, color: _currentStep > 1 ? AppColors.primary : AppColors.border)),
                    _StepDot(label: 'Results', isActive: _currentStep >= 2, isDone: false),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Content
              Expanded(
                child: _currentStep == 0
                    ? _buildCaptureStep()
                    : _currentStep == 1
                        ? _buildAnalyzingStep()
                        : _buildResultsStep(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCaptureStep() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Photo preview or placeholder
          Container(
            width: double.infinity,
            height: 300,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border, width: 0.5),
            ),
            child: _photoBytes != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(24),
                    child: Image.memory(_photoBytes!, fit: BoxFit.cover),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.person_outline, size: 64, color: AppColors.primary.withValues(alpha: 0.3)),
                      const SizedBox(height: 16),
                      const Text('Upload a full-body photo', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                      const SizedBox(height: 8),
                      Text('Stand straight facing the camera\nfor best results', textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
                    ],
                  ),
          ),

          if (_error != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: AppColors.error, size: 20),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13))),
                ],
              ),
            ),
          ],

          const SizedBox(height: 24),

          // Camera button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () => _pickPhoto(ImageSource.camera),
              icon: const Icon(Icons.camera_alt),
              label: const Text('Take Photo'),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            ),
          ),
          const SizedBox(height: 12),
          // Gallery button
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _pickPhoto(ImageSource.gallery),
              icon: const Icon(Icons.photo_library),
              label: const Text('Choose from Gallery'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                side: const BorderSide(color: AppColors.primary),
              ),
            ),
          ),

          const SizedBox(height: 24),
          // Tips
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border, width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('📸 Tips for best results', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                const SizedBox(height: 8),
                _TipRow(text: 'Stand straight, arms at sides'),
                _TipRow(text: 'Wear fitted clothing'),
                _TipRow(text: 'Good lighting, plain background'),
                _TipRow(text: 'Full body visible (head to toe)'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyzingStep() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Show photo being analyzed
          if (_photoBytes != null)
            Container(
              width: 160, height: 200,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.primary, width: 2),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: Image.memory(_photoBytes!, fit: BoxFit.cover),
              ),
            ),
          const SizedBox(height: 32),
          const CircularProgressIndicator(color: AppColors.primary),
          const SizedBox(height: 20),
          const Text('Analyzing your body profile...', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
          const SizedBox(height: 8),
          Text('Detecting measurements, body shape & skin tone', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
        ],
      ),
    );
  }

  Widget _buildResultsStep() {
    final measurements = _analysisResult?['measurements'] as Map<String, dynamic>? ?? {};
    final bodyShape = _analysisResult?['body_shape'] ?? 'unknown';
    final skinTone = _analysisResult?['skin_tone'] ?? 'medium';
    final undertone = _analysisResult?['undertone'] ?? 'neutral';
    final confidence = (_analysisResult?['confidence'] as num?)?.toDouble() ?? 0.0;
    final facial = _analysisResult?['facial_features'] as Map<String, dynamic>? ?? {};

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Success header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: AppColors.gradientPrimary,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle, color: Colors.white, size: 32),
                const SizedBox(width: 12),
                Expanded(child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Analysis Complete!', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Colors.white)),
                    Text('Confidence: ${(confidence * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.8))),
                  ],
                )),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Body shape + skin tone card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border, width: 0.5),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(child: _InfoChip(icon: Icons.accessibility_new, label: 'Body Shape', value: bodyShape.toString().replaceAll('_', ' '))),
                    const SizedBox(width: 12),
                    Expanded(child: _InfoChip(icon: Icons.palette, label: 'Skin Tone', value: '$skinTone ($undertone)')),
                  ],
                ),
                if (facial.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      if (facial['face_shape'] != null && facial['face_shape'] != 'unknown')
                        Expanded(child: _InfoChip(icon: Icons.face, label: 'Face Shape', value: facial['face_shape'])),
                      if (facial['hair_type'] != null && facial['hair_type'] != 'unknown') ...[
                        const SizedBox(width: 12),
                        Expanded(child: _InfoChip(icon: Icons.content_cut, label: 'Hair', value: '${facial['hair_length'] ?? ''} ${facial['hair_type'] ?? ''}')),
                      ],
                    ],
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Measurements card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border, width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('📏 Measurements', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                const SizedBox(height: 16),
                _MeasurementGrid(measurements: measurements),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Action buttons
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () => context.go('/design'),
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Generate My Outfit'),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                setState(() {
                  _currentStep = 0;
                  _photoBytes = null;
                  _analysisResult = null;
                });
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retake Photo'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                side: const BorderSide(color: AppColors.primary),
              ),
            ),
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

class _StepDot extends StatelessWidget {
  final String label;
  final bool isActive;
  final bool isDone;
  const _StepDot({required this.label, required this.isActive, required this.isDone});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 28, height: 28,
          decoration: BoxDecoration(
            color: isDone ? AppColors.success : (isActive ? AppColors.primary : AppColors.surfaceLighter),
            shape: BoxShape.circle,
          ),
          child: Icon(
            isDone ? Icons.check : Icons.circle,
            color: isDone || isActive ? Colors.white : AppColors.textMuted,
            size: 14,
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 10, color: isActive ? AppColors.primaryDark : AppColors.textMuted, fontWeight: isActive ? FontWeight.w600 : FontWeight.w400)),
      ],
    );
  }
}

class _TipRow extends StatelessWidget {
  final String text;
  const _TipRow({required this.text});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          const Icon(Icons.check_circle_outline, size: 16, color: AppColors.success),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InfoChip({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          Icon(icon, color: AppColors.primary, size: 24),
          const SizedBox(height: 6),
          Text(label, style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.primaryDark), textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

class _MeasurementGrid extends StatelessWidget {
  final Map<String, dynamic> measurements;
  const _MeasurementGrid({required this.measurements});

  @override
  Widget build(BuildContext context) {
    final items = <MapEntry<String, String>>[];
    final labels = {
      'height_cm': 'Height',
      'weight_kg': 'Weight',
      'chest_cm': 'Chest',
      'waist_cm': 'Waist',
      'hip_cm': 'Hip',
      'shoulder_width_cm': 'Shoulders',
      'inseam_cm': 'Inseam',
    };
    final units = {
      'height_cm': 'cm',
      'weight_kg': 'kg',
      'chest_cm': 'cm',
      'waist_cm': 'cm',
      'hip_cm': 'cm',
      'shoulder_width_cm': 'cm',
      'inseam_cm': 'cm',
    };

    for (final entry in labels.entries) {
      final val = measurements[entry.key];
      if (val != null) {
        items.add(MapEntry(entry.value, '${val.toStringAsFixed(1)} ${units[entry.key]}'));
      }
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
        childAspectRatio: 1.3,
      ),
      itemCount: items.length,
      itemBuilder: (_, i) => Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppColors.surfaceLighter,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(items[i].value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.primary)),
            const SizedBox(height: 2),
            Text(items[i].key, style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
          ],
        ),
      ),
    );
  }
}
