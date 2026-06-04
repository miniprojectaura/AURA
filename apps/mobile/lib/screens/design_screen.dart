/// Design Studio — Generate outfit designs with AI.
///
/// Features:
/// - Text prompt input
/// - Occasion selector
/// - Color palette picker
/// - Body type selector
/// - SDXL-powered generation
/// - Design history gallery
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

class DesignScreen extends ConsumerStatefulWidget {
  const DesignScreen({super.key});
  @override
  ConsumerState<DesignScreen> createState() => _DesignScreenState();
}

class _DesignScreenState extends ConsumerState<DesignScreen> {
  final _promptController = TextEditingController();
  String? _selectedOccasion;
  String? _selectedBodyType;
  final Set<String> _selectedColors = {};
  bool _isGenerating = false;

  final _occasions = [
    ('💍', 'Wedding'), ('🎉', 'Party'), ('💼', 'Office'),
    ('🪔', 'Festival'), ('☕', 'Casual'), ('🕌', 'Temple'),
    ('🌙', 'Date Night'), ('🎓', 'Graduation'),
  ];

  final _bodyTypes = ['Pear', 'Apple', 'Hourglass', 'Rectangle', 'Inverted Triangle'];

  final _colors = [
    ('Red', Color(0xFFEF4444)), ('Maroon', Color(0xFF7F1D1D)),
    ('Pink', Color(0xFFEC4899)), ('Blue', Color(0xFF3B82F6)),
    ('Navy', Color(0xFF1E3A5F)), ('Green', Color(0xFF10B981)),
    ('Gold', Color(0xFFD4AF37)), ('Purple', Color(0xFF8B5CF6)),
    ('Black', Color(0xFF1A1A1A)), ('White', Color(0xFFF5F5F5)),
    ('Ivory', Color(0xFFFFFDD0)), ('Teal', Color(0xFF14B8A6)),
  ];

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Design Studio'),
        actions: [
          TextButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.history, size: 18),
            label: const Text('History'),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Prompt input
            Text('Describe your dream outfit', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            TextField(
              controller: _promptController,
              maxLines: 3,
              decoration: const InputDecoration(
                hintText: 'e.g., A royal blue Banarasi silk lehenga with gold zari borders for a winter wedding...',
              ),
            ),
            const SizedBox(height: 24),

            // Occasion
            Text('Occasion', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: _occasions.map((o) {
                final isSelected = _selectedOccasion == o.$2;
                return GestureDetector(
                  onTap: () => setState(() => _selectedOccasion = isSelected ? null : o.$2),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.primary.withOpacity(0.15) : AppColors.surfaceLight,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: isSelected ? AppColors.primary : AppColors.border),
                    ),
                    child: Text('${o.$1} ${o.$2}', style: TextStyle(
                      color: isSelected ? AppColors.primary : AppColors.textSecondary,
                      fontSize: 13, fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                    )),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Colors
            Text('Color Palette', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 10, runSpacing: 10,
              children: _colors.map((c) {
                final isSelected = _selectedColors.contains(c.$1);
                return GestureDetector(
                  onTap: () => setState(() {
                    isSelected ? _selectedColors.remove(c.$1) : _selectedColors.add(c.$1);
                  }),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 44, height: 44,
                    decoration: BoxDecoration(
                      color: c.$2,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: isSelected ? AppColors.primary : Colors.transparent,
                        width: isSelected ? 3 : 0,
                      ),
                      boxShadow: isSelected
                          ? [BoxShadow(color: c.$2.withOpacity(0.4), blurRadius: 8)]
                          : null,
                    ),
                    child: isSelected
                        ? Icon(Icons.check, color: c.$2.computeLuminance() > 0.5 ? Colors.black : Colors.white, size: 20)
                        : null,
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Body type
            Text('Body Type (optional)', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: _bodyTypes.map((bt) {
                final isSelected = _selectedBodyType == bt;
                return ChoiceChip(
                  label: Text(bt),
                  selected: isSelected,
                  onSelected: (selected) => setState(() => _selectedBodyType = selected ? bt : null),
                  selectedColor: AppColors.primary.withOpacity(0.2),
                  backgroundColor: AppColors.surfaceLight,
                  labelStyle: TextStyle(
                    color: isSelected ? AppColors.primary : AppColors.textSecondary,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 32),

            // Generate button
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton(
                onPressed: _isGenerating ? null : _generateDesign,
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: Ink(
                  decoration: BoxDecoration(
                    gradient: _isGenerating ? null : AppColors.gradientPrimary,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Container(
                    alignment: Alignment.center,
                    child: _isGenerating
                        ? const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
                              SizedBox(width: 12),
                              Text('Designing...', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                            ],
                          )
                        : const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.auto_awesome, size: 20),
                              SizedBox(width: 8),
                              Text('Generate Design', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                            ],
                          ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 100),
          ],
        ),
      ),
    );
  }

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
        occasion: _selectedOccasion,
        bodyType: _selectedBodyType,
        colors: _selectedColors.toList(),
        styleKeywords: _promptController.text.trim().split(' '),
        culturalContext: null,
      );

      if (mounted) {
        setState(() => _isGenerating = false);
        final responseText = result['response_text'] ?? 'Design generated!';
        final outfits = (result['outfits'] as List?) ?? [];

        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: AppColors.surface,
            title: const Text('✨ Design Result'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(responseText, style: const TextStyle(fontSize: 14)),
                  if (outfits.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const Text('Generated Outfits:', style: TextStyle(fontWeight: FontWeight.w600)),
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
                        child: Text(o['description'] ?? 'Outfit design', style: const TextStyle(fontSize: 13)),
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
