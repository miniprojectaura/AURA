/// Profile Screen — Settings with flat menu list, blue palette.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

// ── State (UNCHANGED) ───────────────────────────────────────────────

class ProfileState {
  final Map<String, dynamic>? user;
  final bool isLoading;
  final String? error;
  ProfileState({this.user, this.isLoading = false, this.error});
  ProfileState copyWith({Map<String, dynamic>? user, bool? isLoading, String? error}) =>
    ProfileState(user: user ?? this.user, isLoading: isLoading ?? this.isLoading, error: error);
}

class ProfileNotifier extends StateNotifier<ProfileState> {
  final ApiService _api;
  ProfileNotifier(this._api) : super(ProfileState(isLoading: true)) { loadProfile(); }

  Future<void> loadProfile() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _api.loadSavedToken();
      final user = await _api.getProfile();
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) { state = state.copyWith(isLoading: false, error: e.toString()); }
  }

  Future<void> updateDisplayName(String name) async {
    try {
      await _api.loadSavedToken();
      final updated = await _api.updateProfile({'display_name': name});
      state = state.copyWith(user: updated);
    } catch (e) { state = state.copyWith(error: 'Update failed: $e'); }
  }

  Future<void> logout() async {
    try { await _api.loadSavedToken(); await _api.logoutServer(); } catch (_) {}
    await _api.logout();
    state = ProfileState();
  }
}

final profileProvider = StateNotifierProvider<ProfileNotifier, ProfileState>((ref) {
  return ProfileNotifier(ref.read(apiServiceProvider));
});

// ── Screen ──────────────────────────────────────────────────────────

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileState = ref.watch(profileProvider);
    final user = profileState.user;
    final displayName = user?['display_name'] ?? 'Fashion Lover';
    final email = user?['email'] ?? '';

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppColors.gradientSurface),
        child: SafeArea(
          child: profileState.isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : SingleChildScrollView(
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
                          const Spacer(),
                          IconButton(
                            icon: const Icon(Icons.close, color: AppColors.textSecondary),
                            onPressed: () => context.go('/home'),
                          ),
                        ],
                      ),
                    ),

                    // Avatar + Name
                    const SizedBox(height: 8),
                    Stack(
                      alignment: Alignment.bottomRight,
                      children: [
                        Container(
                          width: 96, height: 96,
                          decoration: BoxDecoration(
                            gradient: AppColors.gradientPrimary,
                            shape: BoxShape.circle,
                            boxShadow: [BoxShadow(color: AppColors.primary.withValues(alpha: 0.3), blurRadius: 20)],
                          ),
                          child: const Icon(Icons.person, color: Colors.white, size: 48),
                        ),
                        Container(
                          width: 32, height: 32,
                          decoration: BoxDecoration(
                            color: AppColors.primary,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2),
                          ),
                          child: const Icon(Icons.camera_alt, color: Colors.white, size: 16),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(displayName, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.primaryDark)),
                    if (email.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(email, style: TextStyle(fontSize: 14, color: AppColors.textMuted)),
                    ],
                    const SizedBox(height: 28),

                    // Menu items
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: AppColors.border, width: 0.5),
                        ),
                        child: Column(
                          children: [
                            _MenuItem(icon: Icons.person_outline, label: 'Edit Profile', onTap: () => _editDisplayName(context, ref, displayName)),
                            _MenuItem(icon: Icons.account_circle_outlined, label: 'Account Details'),
                            _MenuItem(icon: Icons.shopping_bag_outlined, label: 'E-commerce Accounts'),
                            _MenuItem(icon: Icons.tune, label: 'Preferences'),
                            _MenuItem(icon: Icons.notifications_outlined, label: 'Notifications'),
                            _MenuItem(icon: Icons.lock_outline, label: 'Privacy & Security'),
                            _MenuItem(icon: Icons.help_outline, label: 'Help & Support'),
                            _MenuItem(icon: Icons.info_outline, label: 'About AURA', isLast: true),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Logout
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _handleLogout(context, ref),
                          icon: const Icon(Icons.logout, color: AppColors.error),
                          label: const Text('Log Out', style: TextStyle(color: AppColors.error)),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: AppColors.error),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 40),
                  ],
                ),
              ),
        ),
      ),
    );
  }

  void _editDisplayName(BuildContext context, WidgetRef ref, String current) {
    final controller = TextEditingController(text: current);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit Display Name', style: TextStyle(color: AppColors.primaryDark)),
        content: TextField(controller: controller, decoration: const InputDecoration(hintText: 'Your name')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(onPressed: () {
            Navigator.pop(ctx);
            if (controller.text.trim().isNotEmpty) ref.read(profileProvider.notifier).updateDisplayName(controller.text.trim());
          }, child: const Text('Save')),
        ],
      ),
    );
  }

  void _handleLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Log Out', style: TextStyle(color: AppColors.primaryDark)),
        content: const Text('Are you sure you want to log out?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Log Out', style: TextStyle(color: AppColors.error))),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await ref.read(profileProvider.notifier).logout();
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('access_token');
      await prefs.remove('refresh_token');
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Logged out')));
        context.go('/home');
      }
    }
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool isLast;
  const _MenuItem({required this.icon, required this.label, this.onTap, this.isLast = false});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ListTile(
          leading: Container(
            width: 38, height: 38,
            decoration: BoxDecoration(color: AppColors.surfaceLighter, borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, size: 20, color: AppColors.primary),
          ),
          title: Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: AppColors.textPrimary)),
          trailing: const Icon(Icons.chevron_right, size: 20, color: AppColors.textMuted),
          onTap: onTap ?? () {},
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        ),
        if (!isLast) Divider(height: 1, indent: 70, color: AppColors.border.withValues(alpha: 0.5)),
      ],
    );
  }
}
