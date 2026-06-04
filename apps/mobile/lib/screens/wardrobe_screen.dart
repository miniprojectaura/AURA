/// Wardrobe Screen — My Closet + AI Closet with categories.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

// ── State (UNCHANGED) ───────────────────────────────────────────────

class WardrobeState {
  final List<Map<String, dynamic>> items;
  final bool isLoading;
  final String? error;
  WardrobeState({this.items = const [], this.isLoading = false, this.error});
  WardrobeState copyWith({List<Map<String, dynamic>>? items, bool? isLoading, String? error}) =>
    WardrobeState(items: items ?? this.items, isLoading: isLoading ?? this.isLoading, error: error);
}

class WardrobeNotifier extends StateNotifier<WardrobeState> {
  final ApiService _api;
  WardrobeNotifier(this._api) : super(WardrobeState(isLoading: true)) { loadItems(); }

  Future<void> loadItems() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _api.loadSavedToken();
      final items = await _api.getWardrobeItems();
      state = state.copyWith(items: items.cast<Map<String, dynamic>>(), isLoading: false);
    } catch (e) { state = state.copyWith(isLoading: false, error: e.toString()); }
  }

  Future<void> addItem({required String name, required String category, String? color, String? notes}) async {
    try {
      await _api.loadSavedToken();
      await _api.addWardrobeItem(name: name, category: category, color: color, notes: notes);
      await loadItems();
    } catch (e) { state = state.copyWith(error: 'Failed to add item: $e'); }
  }

  Future<void> deleteItem(String itemId) async {
    try {
      await _api.loadSavedToken();
      await _api.deleteWardrobeItem(itemId);
      await loadItems();
    } catch (e) { state = state.copyWith(error: 'Failed to delete: $e'); }
  }

  Future<String> suggestOutfit(String occasion) async {
    try {
      await _api.loadSavedToken();
      final result = await _api.suggestOutfit(occasion: occasion);
      return result['suggestion'] ?? result['message'] ?? 'No suggestion available';
    } catch (e) { return 'Could not get suggestion: $e'; }
  }
}

final wardrobeProvider = StateNotifierProvider<WardrobeNotifier, WardrobeState>((ref) {
  return WardrobeNotifier(ref.read(apiServiceProvider));
});

// ── Categories ──────────────────────────────────────────────────────

const _categories = [
  (Icons.checkroom, 'All'),
  (Icons.dry_cleaning, 'Tops'),
  (Icons.airline_seat_legroom_normal, 'Bottoms'),
  (Icons.ice_skating, 'Shoes'),
  (Icons.watch, 'Accessories'),
  (Icons.style, 'Outfits'),
];

// ── Screen ──────────────────────────────────────────────────────────

class WardrobeScreen extends ConsumerStatefulWidget {
  const WardrobeScreen({super.key});
  @override
  ConsumerState<WardrobeScreen> createState() => _WardrobeScreenState();
}

class _WardrobeScreenState extends ConsumerState<WardrobeScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  int _selectedCategory = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final wardrobeState = ref.watch(wardrobeProvider);

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
                      child: Text('Wardrobe', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.primaryDark), textAlign: TextAlign.center),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh, color: AppColors.textSecondary),
                      onPressed: () => ref.read(wardrobeProvider.notifier).loadItems(),
                    ),
                  ],
                ),
              ),

              // My Closet / AI Closet tabs
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.surfaceLighter,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicator: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    indicatorSize: TabBarIndicatorSize.tab,
                    labelColor: Colors.white,
                    unselectedLabelColor: AppColors.textSecondary,
                    labelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                    dividerColor: Colors.transparent,
                    tabs: const [Tab(text: 'My Closet'), Tab(text: 'AI Closet')],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Tab content
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    // My Closet
                    _MyClosetTab(
                      wardrobeState: wardrobeState,
                      selectedCategory: _selectedCategory,
                      onCategorySelected: (i) => setState(() => _selectedCategory = i),
                      ref: ref,
                    ),
                    // AI Closet
                    _AiClosetTab(ref: ref),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddDialog(context),
        backgroundColor: AppColors.primary,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  void _showAddDialog(BuildContext context) {
    final nameController = TextEditingController();
    final colorController = TextEditingController();
    String selectedCategory = 'Tops';

    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Padding(
          padding: EdgeInsets.fromLTRB(24, 24, 24, MediaQuery.of(ctx).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(width: 40, height: 4, decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(2))),
              const SizedBox(height: 20),
              const Text('Add New Item', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
              const SizedBox(height: 20),
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Item Name', hintText: 'e.g., Blue Cotton Shirt')),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: selectedCategory,
                decoration: const InputDecoration(labelText: 'Category'),
                items: ['Tops', 'Bottoms', 'Shoes', 'Accessories', 'Outfits', 'Other']
                  .map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: (v) => setSheetState(() => selectedCategory = v!),
              ),
              const SizedBox(height: 12),
              TextField(controller: colorController, decoration: const InputDecoration(labelText: 'Color', hintText: 'e.g., Navy Blue')),
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
                    );
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

// ── My Closet Tab ──────────────────────────────────────────────────

class _MyClosetTab extends StatelessWidget {
  final WardrobeState wardrobeState;
  final int selectedCategory;
  final ValueChanged<int> onCategorySelected;
  final WidgetRef ref;
  const _MyClosetTab({required this.wardrobeState, required this.selectedCategory, required this.onCategorySelected, required this.ref});

  @override
  Widget build(BuildContext context) {
    if (wardrobeState.isLoading) return const Center(child: CircularProgressIndicator(color: AppColors.primary));
    if (wardrobeState.error != null) {
      return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.error_outline, size: 48, color: AppColors.error),
        const SizedBox(height: 12),
        Text(wardrobeState.error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
        const SizedBox(height: 12),
        ElevatedButton(onPressed: () => ref.read(wardrobeProvider.notifier).loadItems(), child: const Text('Retry')),
      ]));
    }

    final categoryName = _categories[selectedCategory].$2;
    final filteredItems = selectedCategory == 0
        ? wardrobeState.items
        : wardrobeState.items.where((i) => i['category'] == categoryName).toList();

    return Column(
      children: [
        // Category pills
        SizedBox(
          height: 80,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: _categories.length,
            itemBuilder: (_, i) {
              final isActive = selectedCategory == i;
              return Padding(
                padding: const EdgeInsets.only(right: 12),
                child: GestureDetector(
                  onTap: () => onCategorySelected(i),
                  child: Column(
                    children: [
                      Container(
                        width: 52, height: 52,
                        decoration: BoxDecoration(
                          color: isActive ? AppColors.primary : AppColors.surface,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: isActive ? AppColors.primary : AppColors.border),
                        ),
                        child: Icon(_categories[i].$1, color: isActive ? Colors.white : AppColors.textSecondary, size: 24),
                      ),
                      const SizedBox(height: 6),
                      Text(_categories[i].$2, style: TextStyle(fontSize: 11, color: isActive ? AppColors.primary : AppColors.textMuted, fontWeight: isActive ? FontWeight.w600 : FontWeight.w400)),
                    ],
                  ),
                ),
              );
            },
          ),
        ),

        // Items grid
        Expanded(
          child: filteredItems.isEmpty
            ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.checkroom, size: 56, color: AppColors.textMuted.withValues(alpha: 0.3)),
                const SizedBox(height: 12),
                const Text('No items yet', style: TextStyle(color: AppColors.textMuted, fontSize: 15)),
                const Text('Tap + to add your first item', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
              ]))
            : GridView.builder(
                padding: const EdgeInsets.all(16),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 0.85,
                ),
                itemCount: filteredItems.length,
                itemBuilder: (_, i) => _ItemCard(item: filteredItems[i], ref: ref),
              ),
        ),
      ],
    );
  }
}

// ── AI Closet Tab ──────────────────────────────────────────────────

class _AiClosetTab extends StatefulWidget {
  final WidgetRef ref;
  const _AiClosetTab({required this.ref});
  @override
  State<_AiClosetTab> createState() => _AiClosetTabState();
}

class _AiClosetTabState extends State<_AiClosetTab> {
  String? _suggestion;
  bool _loading = false;
  String _selectedOccasion = 'Casual';
  final _occasions = ['Casual', 'Wedding', 'Office', 'Party', 'Festival', 'Date Night'];

  Future<void> _getSuggestion() async {
    setState(() { _loading = true; _suggestion = null; });
    final result = await widget.ref.read(wardrobeProvider.notifier).suggestOutfit(_selectedOccasion);
    if (mounted) setState(() { _loading = false; _suggestion = result; });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
                const Text('AI Outfit Suggestion', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                const SizedBox(height: 6),
                const Text('Let AI suggest an outfit from your wardrobe', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: _occasions.map((occ) {
                    final isActive = _selectedOccasion == occ;
                    return GestureDetector(
                      onTap: () => setState(() => _selectedOccasion = occ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: isActive ? AppColors.primary : AppColors.surfaceLighter,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: isActive ? AppColors.primary : AppColors.border),
                        ),
                        child: Text(occ, style: TextStyle(fontSize: 13, color: isActive ? Colors.white : AppColors.textSecondary, fontWeight: isActive ? FontWeight.w600 : FontWeight.w400)),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _loading ? null : _getSuggestion,
                    icon: const Icon(Icons.auto_awesome, size: 18),
                    label: Text(_loading ? 'Thinking...' : 'Get AI Suggestion'),
                  ),
                ),
              ],
            ),
          ),
          if (_suggestion != null) ...[
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(children: [
                    Icon(Icons.auto_awesome, color: AppColors.primary, size: 20),
                    SizedBox(width: 8),
                    Text('AI Suggestion', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                  ]),
                  const SizedBox(height: 12),
                  Text(_suggestion!, style: const TextStyle(fontSize: 14, color: AppColors.textPrimary, height: 1.6)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Item Card ───────────────────────────────────────────────────────

class _ItemCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final WidgetRef ref;
  const _ItemCard({required this.item, required this.ref});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border, width: 0.5),
        boxShadow: [BoxShadow(color: AppColors.primary.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 3))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.surfaceLighter,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
              ),
              child: Stack(children: [
                Center(child: Icon(Icons.checkroom, size: 42, color: AppColors.primary.withValues(alpha: 0.2))),
                Positioned(top: 4, right: 4, child: IconButton(
                  icon: const Icon(Icons.close, size: 16, color: AppColors.textMuted),
                  onPressed: () {
                    final id = item['id']?.toString();
                    if (id != null) ref.read(wardrobeProvider.notifier).deleteItem(id);
                  },
                )),
              ]),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(item['name'] ?? '', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.primaryDark), maxLines: 1, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 4),
              Row(children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: AppColors.surfaceLighter, borderRadius: BorderRadius.circular(6)),
                  child: Text(item['category'] ?? '', style: const TextStyle(fontSize: 10, color: AppColors.primary, fontWeight: FontWeight.w600)),
                ),
                if (item['color'] != null) ...[const SizedBox(width: 6), Text(item['color'], style: const TextStyle(fontSize: 10, color: AppColors.textMuted))],
              ]),
            ]),
          ),
        ],
      ),
    );
  }
}
