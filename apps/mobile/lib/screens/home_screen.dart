/// Home Screen — Hub dashboard with action cards and animated avatar area.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';
import 'profile_screen.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileState = ref.watch(profileProvider);
    final displayName = profileState.user?['display_name'] ?? 'there';
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFD6EBFA), Color(0xFFE8F4FD)],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 16),
                // Top bar — greeting + avatar
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Hello, $displayName 👋',
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.w700,
                              color: AppColors.primaryDark,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Your AI Fashion Designer is ready',
                            style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: () => context.go('/profile'),
                      child: Container(
                        width: 48, height: 48,
                        decoration: BoxDecoration(
                          gradient: AppColors.gradientPrimary,
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.3),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: const Icon(Icons.person, color: Colors.white, size: 24),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                // Avatar / Fashion illustration area
                Expanded(
                  flex: 5,
                  child: Center(
                    child: Container(
                      width: size.width * 0.7,
                      decoration: BoxDecoration(
                        color: AppColors.surface.withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(28),
                        border: Border.all(color: AppColors.border.withValues(alpha: 0.5)),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary.withValues(alpha: 0.08),
                            blurRadius: 40,
                            offset: const Offset(0, 10),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // Animated avatar placeholder (Rive ready)
                          Container(
                            width: 120, height: 120,
                            decoration: BoxDecoration(
                              gradient: AppColors.gradientPrimary,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.primary.withValues(alpha: 0.25),
                                  blurRadius: 24,
                                ),
                              ],
                            ),
                            child: const Icon(Icons.person_outline, color: Colors.white, size: 60),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            'Your Style Avatar',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: AppColors.primaryDark,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Crafting the perfect look for you',
                            style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 20),

                // Action Cards — Hub navigation
                Expanded(
                  flex: 4,
                  child: Column(
                    children: [
                      _HubCard(
                        icon: Icons.auto_awesome,
                        label: 'Generate New Outfit',
                        subtitle: 'AI-powered fashion design',
                        onTap: () => context.go('/design'),
                      ),
                      const SizedBox(height: 10),
                      _HubCard(
                        icon: Icons.accessibility_new,
                        label: 'Body Profile',
                        subtitle: 'Set up or update your measurements',
                        onTap: () => context.go('/body-setup'),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: _HubCardSmall(
                              icon: Icons.checkroom,
                              label: 'Wardrobe',
                              onTap: () => context.go('/wardrobe'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _HubCardSmall(
                              icon: Icons.chat_bubble_rounded,
                              label: 'Chat',
                              onTap: () => context.go('/chat'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _HubCardSmall(
                              icon: Icons.settings,
                              label: 'Settings',
                              onTap: () => context.go('/profile'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HubCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;
  const _HubCard({required this.icon, required this.label, required this.subtitle, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border.withValues(alpha: 0.5)),
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.06),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48, height: 48,
              decoration: BoxDecoration(
                gradient: AppColors.gradientPrimary,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.primaryDark)),
                  Text(subtitle, style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios, size: 16, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class _HubCardSmall extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _HubCardSmall({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 18),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border.withValues(alpha: 0.5)),
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.05),
              blurRadius: 12,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Column(
          children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: AppColors.surfaceLighter,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: AppColors.primary, size: 22),
            ),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.primaryDark)),
          ],
        ),
      ),
    );
  }
}
