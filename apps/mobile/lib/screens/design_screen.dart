/// Design Studio — Generate outfit designs with AI voice + text input.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

class DesignScreen extends ConsumerStatefulWidget {
  const DesignScreen({super.key});
  @override
  ConsumerState<DesignScreen> createState() => _DesignScreenState();
}

class _DesignScreenState extends ConsumerState<DesignScreen> {
  final _promptController = TextEditingController();
  bool _isGenerating = false;
  bool _isListening = false;

  void _toggleListening() {
    if (_isListening) {
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('🎤 Voice input: speak now and type what you said')),
      );
      // Auto-stop after 5 seconds visual feedback
      Future.delayed(const Duration(seconds: 5), () {
        if (mounted && _isListening) setState(() => _isListening = false);
      });
    }
  }

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
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
                      child: Text(
                        'Generate New Outfit',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.primaryDark),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),

              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Voice Input Card
                      GestureDetector(
                        onTap: _toggleListening,
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: AppColors.surface,
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(
                              color: _isListening ? AppColors.primary : AppColors.border,
                              width: _isListening ? 2 : 0.5,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.primary.withValues(alpha: _isListening ? 0.15 : 0.05),
                                blurRadius: 20,
                                offset: const Offset(0, 6),
                              ),
                            ],
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 56, height: 56,
                                decoration: BoxDecoration(
                                  color: _isListening
                                      ? AppColors.primary
                                      : AppColors.surfaceLighter,
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Icon(
                                  _isListening ? Icons.mic : Icons.mic_none,
                                  color: _isListening ? Colors.white : AppColors.primary,
                                  size: 28,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _isListening ? 'Listening...' : 'Speak Your Style',
                                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.primaryDark),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      _isListening
                                          ? 'Tap to stop recording'
                                          : 'Describe the outfit you want in your own words',
                                      style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 20),

                      // Text Prompt Card
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(color: AppColors.border, width: 0.5),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.05),
                              blurRadius: 20,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: 56, height: 56,
                                  decoration: BoxDecoration(
                                    color: AppColors.surfaceLighter,
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: const Icon(Icons.edit_note, color: AppColors.primary, size: 28),
                                ),
                                const SizedBox(width: 16),
                                const Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Or Type a Prompt', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                                      SizedBox(height: 4),
                                      Text('Type what you have in mind and let AI design for you', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 20),
                            // Suggestion chips
                            Wrap(
                              spacing: 8, runSpacing: 8,
                              children: [
                                _SuggestionChip(label: 'Wedding lehenga', onTap: () => _promptController.text = 'Wedding lehenga in red silk with gold embroidery'),
                                _SuggestionChip(label: 'Office kurta', onTap: () => _promptController.text = 'Elegant office kurta in navy blue cotton'),
                                _SuggestionChip(label: 'Party wear', onTap: () => _promptController.text = 'Stylish party wear outfit in black and gold'),
                                _SuggestionChip(label: 'Casual summer', onTap: () => _promptController.text = 'Light casual summer outfit in pastel colors'),
                              ],
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 100),
                    ],
                  ),
                ),
              ),

              // Bottom input bar
              Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  border: Border(top: BorderSide(color: AppColors.border.withValues(alpha: 0.5))),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.surfaceLight,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: TextField(
                          controller: _promptController,
                          decoration: const InputDecoration(
                            hintText: 'Type your prompt here...',
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          ),
                          maxLines: 1,
                          style: const TextStyle(color: AppColors.textPrimary),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    GestureDetector(
                      onTap: _isGenerating ? null : _generateDesign,
                      child: Container(
                        width: 52, height: 52,
                        decoration: BoxDecoration(
                          gradient: _isGenerating ? null : AppColors.gradientPrimary,
                          color: _isGenerating ? AppColors.textMuted : null,
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: _isGenerating ? null : [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.3),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: _isGenerating
                          ? const Padding(
                              padding: EdgeInsets.all(14),
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.send_rounded, color: Colors.white, size: 24),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── API call — UNCHANGED LOGIC ──────────────────────────────────
  Future<void> _generateDesign() async {
    if (_promptController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please describe your outfit')),
      );
      return;
    }

    setState(() => _isGenerating = true);

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.loadSavedToken();
      final result = await apiService.generateDesign(
        styleKeywords: _promptController.text.trim().split(' '),
      );

      if (mounted) {
        setState(() => _isGenerating = false);
        final responseText = result['response_text'] ?? 'Design generated!';
        final outfits = (result['outfits'] as List?) ?? [];

        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: AppColors.surface,
            title: const Text('✨ Design Result', style: TextStyle(color: AppColors.primaryDark)),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(responseText, style: const TextStyle(fontSize: 14, color: AppColors.textPrimary)),
                  if (outfits.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const Text('Generated Outfits:', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                    const SizedBox(height: 8),
                    ...outfits.map((o) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceLight,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(o['description'] ?? 'Outfit design', style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
                      ),
                    )),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isGenerating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Design generation failed: $e')),
        );
      }
    }
  }
}

class _SuggestionChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _SuggestionChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.surfaceLighter,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: Text(label, style: const TextStyle(fontSize: 12, color: AppColors.primary, fontWeight: FontWeight.w500)),
      ),
    );
  }
}
