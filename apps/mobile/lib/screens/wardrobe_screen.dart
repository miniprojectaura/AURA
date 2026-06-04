/// Wardrobe Screen — Manage clothing items by category.
///
/// Features:
/// - Tab-based categories (All, Ethnic, Western, Accessories)
/// - Add item via manual entry
/// - Outfit suggestions from wardrobe
/// - Real API-backed CRUD operations
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

// ── Wardrobe State ──────────────────────────────────────────────────

class WardrobeState {
  final List<Map<String, dynamic>> items;
  final bool isLoading;
  final String? error;
  WardrobeState({this.items = const [], this.isLoading = false, this.error});
  WardrobeState copyWith({List<Map<String, dynamic>>? items, bool? isLoading, String? error}) =>
    WardrobeState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
}

class WardrobeNotifier extends StateNotifier<WardrobeState> {
  final ApiService _api;

  WardrobeNotifier(this._api) : super(WardrobeState(isLoading: true)) {
    loadItems();
  }

  Future<void> loadItems() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _api.loadSavedToken();
      final items = await _api.getWardrobeItems();
      state = state.copyWith(
        items: items.cast<Map<String, dynamic>>(),
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> addItem({
    required String name,
    required String category,
    String? color,
    String? notes,
  }) async {
    try {
      await _api.loadSavedToken();
      await _api.addWardrobeItem(
        name: name,
        category: category,
        color: color,
        notes: notes,
      );
      await loadItems(); // Refresh from server
    } catch (e) {
      state = state.copyWith(error: 'Failed to add item: $e');
    }
  }

  Future<void> deleteItem(String itemId) async {
    try {
      await _api.loadSavedToken();
      await _api.deleteWardrobeItem(itemId);
      await loadItems();
    } catch (e) {
      state = state.copyWith(error: 'Failed to delete: $e');
    }
  }

  Future<String> suggestOutfit(String occasion) async {
    try {
      await _api.loadSavedToken();
      final result = await _api.suggestOutfit(occasion: occasion);
      return result['suggestion'] ?? result['message'] ?? 'No suggestion available';
    } catch (e) {
      return 'Could not get suggestion: $e';
    }
  }
}

final wardrobeProvider = StateNotifierProvider<WardrobeNotifier, WardrobeState>((ref) {
  return WardrobeNotifier(ref.read(apiServiceProvider));
});

// ── Screen ──────────────────────────────────────────────────────────

class WardrobeScreen extends ConsumerWidget {
  const WardrobeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final wardrobeState = ref.watch(wardrobeProvider);

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
              onPressed: () => _showSuggestDialog(context, ref),
            ),
            IconButton(
              icon: const Icon(Icons.refresh, color: AppColors.textSecondary),
              tooltip: 'Refresh',
              onPressed: () => ref.read(wardrobeProvider.notifier).loadItems(),
            ),
          ],
        ),
        body: wardrobeState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : wardrobeState.error != null
            ? Center(child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.error_outline, size: 48, color: AppColors.error),
                  const SizedBox(height: 12),
                  Text(wardrobeState.error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textMuted)),
                  const SizedBox(height: 12),
                  ElevatedButton(onPressed: () => ref.read(wardrobeProvider.notifier).loadItems(), child: const Text('Retry')),
                ],
              ))
            : TabBarView(
                children: [
                  _WardrobeGrid(items: wardrobeState.items, ref: ref),
                  _WardrobeGrid(items: wardrobeState.items.where((i) => i['category'] == 'Ethnic').toList(), ref: ref),
                  _WardrobeGrid(items: wardrobeState.items.where((i) => i['category'] == 'Western').toList(), ref: ref),
                  _WardrobeGrid(items: wardrobeState.items.where((i) => i['category'] == 'Accessories').toList(), ref: ref),
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

  void _showSuggestDialog(BuildContext context, WidgetRef ref) {
    final occasions = ['Wedding', 'Party', 'Office', 'Casual', 'Festival', 'Date Night'];
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Choose Occasion for Outfit Suggestion', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: occasions.map((occ) => ActionChip(
                label: Text(occ),
                onPressed: () async {
                  Navigator.pop(ctx);
                  final suggestion = await ref.read(wardrobeProvider.notifier).suggestOutfit(occ);
                  if (context.mounted) {
                    showDialog(
                      context: context,
                      builder: (c) => AlertDialog(
                        backgroundColor: AppColors.surface,
                        title: Text('Outfit for $occ'),
                        content: Text(suggestion),
                        actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Close'))],
                      ),
                    );
                  }
                },
              )).toList(),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  void _showAddDialog(BuildContext context, WidgetRef ref) {
    final nameController = TextEditingController();
    final colorController = TextEditingController();
    final notesController = TextEditingController();
    String selectedCategory = 'Ethnic';

    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Padding(
          padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(ctx).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(width: 40, height: 4, decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2))),
              const SizedBox(height: 20),
              Text('Add to Wardrobe', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Item Name', hintText: 'e.g., Red Banarasi Saree')),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: selectedCategory,
                decoration: const InputDecoration(labelText: 'Category'),
                dropdownColor: AppColors.surface,
                items: ['Ethnic', 'Western', 'Accessories', 'Footwear', 'Other']
                  .map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: (v) => setSheetState(() => selectedCategory = v!),
              ),
              const SizedBox(height: 12),
              TextField(controller: colorController, decoration: const InputDecoration(labelText: 'Color (optional)', hintText: 'e.g., Red')),
              const SizedBox(height: 12),
              TextField(controller: notesController, decoration: const InputDecoration(labelText: 'Notes (optional)', hintText: 'e.g., Gift from mom')),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () async {
                    if (nameController.text.trim().isEmpty) return;
                    Navigator.pop(ctx);
                    await ref.read(wardrobeProvider.notifier).addItem(
                      name: nameController.text.trim(),
                      category: selectedCategory,
                      color: colorController.text.trim().isEmpty ? null : colorController.text.trim(),
                      notes: notesController.text.trim().isEmpty ? null : notesController.text.trim(),
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Item added!')));
                    }
                  },
                  child: const Text('Add Item'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WardrobeGrid extends StatelessWidget {
  final List<Map<String, dynamic>> items;
  final WidgetRef ref;
  const _WardrobeGrid({required this.items, required this.ref});

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.checkroom, size: 64, color: AppColors.textMuted.withValues(alpha: 0.3)),
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
      itemBuilder: (context, index) => _WardrobeCard(item: items[index], ref: ref),
    );
  }
}

class _WardrobeCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final WidgetRef ref;
  const _WardrobeCard({required this.item, required this.ref});

  Color get _categoryColor {
    switch (item['category']) {
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
              child: Stack(
                children: [
                  Center(child: Icon(Icons.checkroom, size: 48, color: _categoryColor.withValues(alpha: 0.3))),
                  Positioned(
                    top: 4, right: 4,
                    child: IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18, color: AppColors.error),
                      onPressed: () {
                        final id = item['id']?.toString();
                        if (id != null) {
                          ref.read(wardrobeProvider.notifier).deleteItem(id);
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item['name'] ?? 'Unknown', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500), maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: _categoryColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(item['category'] ?? '', style: TextStyle(fontSize: 10, color: _categoryColor, fontWeight: FontWeight.w600)),
                    ),
                    if (item['color'] != null) ...[
                      const SizedBox(width: 6),
                      Text(item['color'], style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
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
