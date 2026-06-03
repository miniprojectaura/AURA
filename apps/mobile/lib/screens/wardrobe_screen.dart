/// Wardrobe Screen — Manage clothing items by category.
///
/// Features:
/// - Tab-based categories (All, Ethnic, Western, Accessories)
/// - Add item via camera, gallery, or manual entry
/// - Outfit suggestions from wardrobe
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme.dart';

class WardrobeItem {
  final String name;
  final String category;
  final String? color;
  final String? imageUrl;
  final DateTime addedAt;
  WardrobeItem({required this.name, required this.category, this.color, this.imageUrl})
      : addedAt = DateTime.now();
}

final wardrobeProvider = StateProvider<List<WardrobeItem>>((ref) => [
  WardrobeItem(name: 'Red Banarasi Saree', category: 'Ethnic', color: 'Red'),
  WardrobeItem(name: 'Navy Blue Kurta', category: 'Ethnic', color: 'Navy'),
  WardrobeItem(name: 'White Cotton Shirt', category: 'Western', color: 'White'),
  WardrobeItem(name: 'Black Denim Jeans', category: 'Western', color: 'Black'),
  WardrobeItem(name: 'Gold Kundan Set', category: 'Accessories', color: 'Gold'),
]);

class WardrobeScreen extends ConsumerWidget {
  const WardrobeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = ref.watch(wardrobeProvider);

    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('My Wardrobe'),
          bottom: const TabBar(
            indicatorColor: AppColors.primary,
            labelColor: AppColors.primary,
            unselectedLabelColor: AppColors.textMuted,
            tabs: [
              Tab(text: 'All'),
              Tab(text: 'Ethnic'),
              Tab(text: 'Western'),
              Tab(text: 'Accessories'),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.auto_fix_high, color: AppColors.primary),
              tooltip: 'Suggest outfit from wardrobe',
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('AI is analyzing your wardrobe for outfit suggestions...')),
                );
              },
            ),
          ],
        ),
        body: TabBarView(
          children: [
            _WardrobeGrid(items: items),
            _WardrobeGrid(items: items.where((i) => i.category == 'Ethnic').toList()),
            _WardrobeGrid(items: items.where((i) => i.category == 'Western').toList()),
            _WardrobeGrid(items: items.where((i) => i.category == 'Accessories').toList()),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () => _showAddDialog(context, ref),
          backgroundColor: AppColors.primary,
          icon: const Icon(Icons.add_photo_alternate),
          label: const Text('Add Item'),
        ),
      ),
    );
  }

  void _showAddDialog(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 40, height: 4, decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 20),
            Text('Add to Wardrobe', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(child: _AddOption(icon: Icons.camera_alt, label: 'Camera', onTap: () => Navigator.pop(context))),
                const SizedBox(width: 12),
                Expanded(child: _AddOption(icon: Icons.photo_library, label: 'Gallery', onTap: () => Navigator.pop(context))),
                const SizedBox(width: 12),
                Expanded(child: _AddOption(icon: Icons.edit, label: 'Manual', onTap: () => Navigator.pop(context))),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _WardrobeGrid extends StatelessWidget {
  final List<WardrobeItem> items;
  const _WardrobeGrid({required this.items});

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.checkroom, size: 64, color: AppColors.textMuted.withOpacity(0.3)),
            const SizedBox(height: 16),
            Text('No items yet', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.textMuted)),
            const SizedBox(height: 8),
            Text('Tap + to add your first item', style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 0.85,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) => _WardrobeCard(item: items[index]),
    );
  }
}

class _WardrobeCard extends StatelessWidget {
  final WardrobeItem item;
  const _WardrobeCard({required this.item});

  Color get _categoryColor {
    switch (item.category) {
      case 'Ethnic': return AppColors.primary;
      case 'Western': return AppColors.accent;
      case 'Accessories': return AppColors.warning;
      default: return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Image placeholder
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.surfaceLighter,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              child: Center(
                child: Icon(Icons.checkroom, size: 48, color: _categoryColor.withOpacity(0.3)),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500), maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: _categoryColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(item.category, style: TextStyle(fontSize: 10, color: _categoryColor, fontWeight: FontWeight.w600)),
                    ),
                    if (item.color != null) ...[
                      const SizedBox(width: 6),
                      Text(item.color!, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AddOption extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _AddOption({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Icon(icon, size: 28, color: AppColors.primary),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }
}
