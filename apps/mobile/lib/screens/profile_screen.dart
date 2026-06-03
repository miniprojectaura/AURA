/// Profile Screen — User settings, body profile, style preferences, and app settings.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Avatar
            Center(
              child: Column(
                children: [
                  Container(
                    width: 88, height: 88,
                    decoration: BoxDecoration(
                      gradient: AppColors.gradientPrimary,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.person, color: Colors.white, size: 44),
                  ),
                  const SizedBox(height: 12),
                  Text('Fashion Enthusiast', style: Theme.of(context).textTheme.titleMedium),
                  Text('Joined May 2026', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(height: 28),

            // Body Profile
            _Section(
              title: 'Body Profile',
              icon: Icons.straighten,
              children: [
                _SettingTile(icon: Icons.height, title: 'Height', subtitle: 'Not set', onTap: () {}),
                _SettingTile(icon: Icons.monitor_weight, title: 'Body Type', subtitle: 'Not set', onTap: () {}),
                _SettingTile(icon: Icons.color_lens, title: 'Skin Tone', subtitle: 'Not analyzed', onTap: () {}),
                _SettingTile(icon: Icons.camera_alt, title: 'Create 3D Avatar', subtitle: 'Upload front & side photos', onTap: () {}),
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
                _SettingTile(icon: Icons.favorite, title: 'Liked Designs', subtitle: '0 designs saved', onTap: () {}),
              ],
            ),
            const SizedBox(height: 16),

            // App Settings
            _Section(
              title: 'Settings',
              icon: Icons.settings,
              children: [
                _SettingTile(icon: Icons.language, title: 'Language', subtitle: 'English', onTap: () {}),
                _SettingTile(icon: Icons.notifications, title: 'Notifications', subtitle: 'Enabled', onTap: () {}),
                _SettingTile(icon: Icons.cloud_off, title: 'Offline Mode', subtitle: 'Disabled', onTap: () {}),
                _SettingTile(icon: Icons.dark_mode, title: 'Theme', subtitle: 'Dark', onTap: () {}),
              ],
            ),
            const SizedBox(height: 16),

            // Data & Privacy
            _Section(
              title: 'Data & Privacy',
              icon: Icons.shield,
              children: [
                _SettingTile(icon: Icons.download, title: 'Export My Data', subtitle: 'Download all your data', onTap: () {}),
                _SettingTile(icon: Icons.delete_forever, title: 'Delete Account', subtitle: 'GDPR data deletion', onTap: () {}, isDestructive: true),
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
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      TextButton(onPressed: () {}, child: const Text('Privacy Policy', style: TextStyle(fontSize: 12))),
                      const Text('•', style: TextStyle(color: AppColors.textMuted)),
                      TextButton(onPressed: () {}, child: const Text('Terms of Service', style: TextStyle(fontSize: 12))),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Logout
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () {},
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
          color: (isDestructive ? AppColors.error : AppColors.primary).withOpacity(0.1),
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
