/// Profile Screen — User settings, body profile, style preferences, and app settings.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/theme.dart';
import '../services/api_service.dart';

// ── Profile State ──────────────────────────────────────────────────

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
  ProfileNotifier(this._api) : super(ProfileState(isLoading: true)) {
    loadProfile();
  }

  Future<void> loadProfile() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _api.loadSavedToken();
      final user = await _api.getProfile();
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> updateDisplayName(String name) async {
    try {
      await _api.loadSavedToken();
      final updated = await _api.updateProfile({'display_name': name});
      state = state.copyWith(user: updated);
    } catch (e) {
      state = state.copyWith(error: 'Update failed: $e');
    }
  }

  Future<void> logout() async {
    try {
      await _api.loadSavedToken();
      await _api.logoutServer();
    } catch (_) {}
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
    final createdAt = user?['created_at'] ?? '';
    final language = user?['language_preference'] ?? 'en';

    String joinDate = '';
    if (createdAt.isNotEmpty) {
      try {
        final dt = DateTime.parse(createdAt);
        final months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        joinDate = 'Joined ${months[dt.month - 1]} ${dt.year}';
      } catch (_) {
        joinDate = '';
      }
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: profileState.isLoading
        ? const Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Avatar
            Center(
              child: Column(
                children: [
                  Container(
                    width: 88, height: 88,
                    decoration: BoxDecoration(gradient: AppColors.gradientPrimary, shape: BoxShape.circle),
                    child: const Icon(Icons.person, color: Colors.white, size: 44),
                  ),
                  const SizedBox(height: 12),
                  Text(displayName, style: Theme.of(context).textTheme.titleMedium),
                  if (email.isNotEmpty) Text(email, style: Theme.of(context).textTheme.bodySmall),
                  if (joinDate.isNotEmpty) Text(joinDate, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(height: 28),

            if (profileState.error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(color: AppColors.error.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
                child: Text(profileState.error!, style: const TextStyle(color: AppColors.error, fontSize: 12)),
              ),
            ],

            // Body Profile
            _Section(
              title: 'Body Profile',
              icon: Icons.straighten,
              children: [
                _SettingTile(icon: Icons.height, title: 'Height', subtitle: 'Not set', onTap: () {}),
                _SettingTile(icon: Icons.monitor_weight, title: 'Body Type', subtitle: 'Not set', onTap: () {}),
                _SettingTile(icon: Icons.color_lens, title: 'Skin Tone', subtitle: 'Not analyzed', onTap: () {}),
              ],
            ),
            const SizedBox(height: 16),

            // Style Preferences
            _Section(
              title: 'Style Preferences',
              icon: Icons.auto_awesome,
              children: [
                _SettingTile(icon: Icons.palette, title: 'Favorite Colors', subtitle: 'Not set', onTap: () {}),
                _SettingTile(icon: Icons.checkroom, title: 'Preferred Styles', subtitle: 'Ethnic, Indo-Western', onTap: () {}),
                _SettingTile(icon: Icons.monetization_on, title: 'Budget Range', subtitle: '₹2,000 - ₹10,000', onTap: () {}),
              ],
            ),
            const SizedBox(height: 16),

            // Account
            _Section(
              title: 'Account',
              icon: Icons.settings,
              children: [
                _SettingTile(
                  icon: Icons.person_outline,
                  title: 'Display Name',
                  subtitle: displayName,
                  onTap: () => _editDisplayName(context, ref, displayName),
                ),
                _SettingTile(icon: Icons.language, title: 'Language', subtitle: language == 'en' ? 'English' : language, onTap: () {}),
                _SettingTile(icon: Icons.dark_mode, title: 'Theme', subtitle: 'Dark', onTap: () {}),
              ],
            ),
            const SizedBox(height: 16),

            // App info
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  Text('AI Fashion Designer', style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 4),
                  Text('Version 1.0.0', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Logout
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _handleLogout(context, ref),
                icon: const Icon(Icons.logout, color: AppColors.error),
                label: const Text('Log Out', style: TextStyle(color: AppColors.error)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            const SizedBox(height: 100),
          ],
        ),
      ),
    );
  }

  void _editDisplayName(BuildContext context, WidgetRef ref, String current) {
    final controller = TextEditingController(text: current);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Edit Display Name'),
        content: TextField(controller: controller, decoration: const InputDecoration(hintText: 'Your name')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              if (controller.text.trim().isNotEmpty) {
                ref.read(profileProvider.notifier).updateDisplayName(controller.text.trim());
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _handleLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Log Out'),
        content: const Text('Are you sure you want to log out?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Log Out', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await ref.read(profileProvider.notifier).logout();
      // Clear saved tokens
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

class _Section extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;
  const _Section({required this.title, required this.icon, required this.children});

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
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
            child: Row(
              children: [
                Icon(icon, size: 18, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primary)),
              ],
            ),
          ),
          ...children,
        ],
      ),
    );
  }
}

class _SettingTile extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final VoidCallback onTap;
  final bool isDestructive;
  const _SettingTile({required this.icon, required this.title, required this.subtitle, required this.onTap, this.isDestructive = false});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Container(
        width: 36, height: 36,
        decoration: BoxDecoration(
          color: (isDestructive ? AppColors.error : AppColors.primary).withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, size: 18, color: isDestructive ? AppColors.error : AppColors.primary),
      ),
      title: Text(title, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: isDestructive ? AppColors.error : AppColors.textPrimary)),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
      trailing: const Icon(Icons.chevron_right, size: 18, color: AppColors.textMuted),
      onTap: onTap,
    );
  }
}
