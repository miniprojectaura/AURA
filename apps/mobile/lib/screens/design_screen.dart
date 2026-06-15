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

  // ── API call — ENHANCED with full pipeline results ──────────────
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
        _showOutfitResults(result);
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

  void _showOutfitResults(Map<String, dynamic> result) {
    final responseText = result['response_text'] ?? 'Design generated!';
    final outfits = (result['outfits'] as List?) ?? [];
    final design = result['design'] as Map<String, dynamic>?;
    final bodyUsed = result['body_profile_used'] == true;
    final advice = result['body_shape_advice'] as String? ?? '';
    final palette = design?['color_palette'] as Map<String, dynamic>?;
    final outfitName = design?['outfit_name'] ?? 'Custom Outfit';
    final hair = design?['hair_suggestion'] as Map<String, dynamic>?;
    final makeup = design?['makeup_suggestion'] as Map<String, dynamic>?;

    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _OutfitResultScreen(
        outfitName: outfitName,
        responseText: responseText,
        outfits: outfits,
        palette: palette,
        bodyUsed: bodyUsed,
        advice: advice,
        hair: hair,
        makeup: makeup,
      ),
    ));
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

// ═══════════════════════════════════════════════════════════════
// Full-page outfit result screen
// ═══════════════════════════════════════════════════════════════
class _OutfitResultScreen extends StatelessWidget {
  final String outfitName;
  final String responseText;
  final List outfits;
  final Map<String, dynamic>? palette;
  final bool bodyUsed;
  final String advice;
  final Map<String, dynamic>? hair;
  final Map<String, dynamic>? makeup;

  const _OutfitResultScreen({
    required this.outfitName,
    required this.responseText,
    required this.outfits,
    this.palette,
    required this.bodyUsed,
    required this.advice,
    this.hair,
    this.makeup,
  });

  IconData _garmentIcon(String type) {
    switch (type.toLowerCase()) {
      case 'headwear': return Icons.face;
      case 'top': return Icons.checkroom;
      case 'bottom': return Icons.straighten;
      case 'dress': return Icons.dry_cleaning;
      case 'outerwear': return Icons.layers;
      case 'footwear': return Icons.snowshoeing;
      case 'accessory': return Icons.watch;
      case 'jewelry': return Icons.diamond;
      case 'innerwear': return Icons.shield;
      default: return Icons.checkroom;
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
                      onPressed: () => Navigator.pop(context),
                    ),
                    const Expanded(
                      child: Text('Your Outfit', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.primaryDark), textAlign: TextAlign.center),
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
                      // Outfit name header
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          gradient: AppColors.gradientPrimary,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('✨ $outfitName', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Colors.white)),
                            const SizedBox(height: 8),
                            Text(responseText, style: TextStyle(fontSize: 14, color: Colors.white.withValues(alpha: 0.9))),
                            if (bodyUsed) ...[
                              const SizedBox(height: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: const Text('👤 Personalized to your body', style: TextStyle(fontSize: 12, color: Colors.white)),
                              ),
                            ],
                          ],
                        ),
                      ),

                      // Color palette
                      if (palette != null && palette!['primary'] != null) ...[
                        const SizedBox(height: 20),
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
                              const Text('🎨 Color Palette', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  _ColorCircle(label: 'Primary', hex: palette!['primary'] ?? '#000'),
                                  const SizedBox(width: 16),
                                  _ColorCircle(label: 'Secondary', hex: palette!['secondary'] ?? '#888'),
                                  const SizedBox(width: 16),
                                  _ColorCircle(label: 'Accent', hex: palette!['accent'] ?? '#fff'),
                                ],
                              ),
                              if (palette!['reasoning'] != null) ...[
                                const SizedBox(height: 8),
                                Text(palette!['reasoning'], style: TextStyle(fontSize: 12, color: AppColors.textMuted, fontStyle: FontStyle.italic)),
                              ],
                            ],
                          ),
                        ),
                      ],

                      // Body shape advice
                      if (advice.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.accessibility_new, color: AppColors.primary, size: 20),
                              const SizedBox(width: 10),
                              Expanded(child: Text(advice, style: const TextStyle(fontSize: 13, color: AppColors.primaryDark))),
                            ],
                          ),
                        ),
                      ],

                      // Garments list
                      if (outfits.isNotEmpty) ...[
                        const SizedBox(height: 20),
                        const Text('👗 Garments', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                        const SizedBox(height: 12),
                        ...outfits.map((g) {
                          final type = g['type']?.toString() ?? '';
                          final name = g['name']?.toString() ?? 'Item';
                          final desc = g['description']?.toString() ?? '';
                          final color = g['color']?.toString() ?? '';
                          final fabric = g['fabric']?.toString() ?? '';
                          final fitNotes = g['fit_notes']?.toString() ?? '';
                          final tip = g['styling_tip']?.toString() ?? '';
                          final price = g['estimated_price_inr'];
                          final keywords = g['search_keywords']?.toString() ?? '';

                          return Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: AppColors.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: AppColors.border, width: 0.5),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      width: 40, height: 40,
                                      decoration: BoxDecoration(
                                        color: AppColors.surfaceLighter,
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Icon(_garmentIcon(type), color: AppColors.primary, size: 22),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(name, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                                        if (type.isNotEmpty)
                                          Text(type.toUpperCase(), style: TextStyle(fontSize: 11, color: AppColors.textMuted, fontWeight: FontWeight.w500, letterSpacing: 0.5)),
                                      ],
                                    )),
                                    if (price != null)
                                      Text('₹${price}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primary)),
                                  ],
                                ),
                                if (desc.isNotEmpty) ...[
                                  const SizedBox(height: 10),
                                  Text(desc, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                                ],
                                const SizedBox(height: 8),
                                Wrap(spacing: 8, runSpacing: 4, children: [
                                  if (color.isNotEmpty) _TagChip(icon: Icons.palette, text: color),
                                  if (fabric.isNotEmpty) _TagChip(icon: Icons.texture, text: fabric),
                                ]),
                                if (fitNotes.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  Text('👤 $fitNotes', style: TextStyle(fontSize: 12, color: AppColors.primary.withValues(alpha: 0.8), fontStyle: FontStyle.italic)),
                                ],
                                if (tip.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text('💡 $tip', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                                ],
                              ],
                            ),
                          );
                        }),
                      ],

                      // Hair + Makeup
                      if (hair != null || makeup != null) ...[
                        const SizedBox(height: 16),
                        const Text('💇 Styling Suggestions', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                        const SizedBox(height: 12),
                        if (hair != null && hair!['style'] != null)
                          _SuggestionCard(icon: Icons.face_retouching_natural, title: 'Hair', text: hair!['style'], reason: hair!['reasoning']),
                        if (makeup != null && makeup!['style'] != null) ...[
                          const SizedBox(height: 8),
                          _SuggestionCard(icon: Icons.brush, title: 'Makeup', text: makeup!['style'], reason: makeup!['reasoning']),
                        ],
                      ],

                      const SizedBox(height: 40),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ColorCircle extends StatelessWidget {
  final String label;
  final String hex;
  const _ColorCircle({required this.label, required this.hex});

  Color _parseHex(String h) {
    try {
      final cleaned = h.replaceAll('#', '');
      return Color(int.parse('FF$cleaned', radix: 16));
    } catch (_) {
      return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 36, height: 36,
          decoration: BoxDecoration(
            color: _parseHex(hex),
            shape: BoxShape.circle,
            border: Border.all(color: AppColors.border, width: 1),
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
      ],
    );
  }
}

class _TagChip extends StatelessWidget {
  final IconData icon;
  final String text;
  const _TagChip({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceLighter,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: AppColors.textMuted),
          const SizedBox(width: 4),
          Text(text, style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  final String? reason;
  const _SuggestionCard({required this.icon, required this.title, required this.text, this.reason});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border, width: 0.5),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.primary, size: 22),
          const SizedBox(width: 10),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
              const SizedBox(height: 2),
              Text(text, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
              if (reason != null && reason!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(reason!, style: TextStyle(fontSize: 12, color: AppColors.textMuted, fontStyle: FontStyle.italic)),
              ],
            ],
          )),
        ],
      ),
    );
  }
}

