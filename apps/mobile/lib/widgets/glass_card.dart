library;
/// Glassmorphism card widget — reusable glass-like container.
import 'dart:ui';
import 'package:flutter/material.dart';
import '../core/theme.dart';

class GlassCard extends StatelessWidget {
  final Widget child;
  final double blur;
  final double opacity;
  final EdgeInsets padding;
  final BorderRadius borderRadius;

  const GlassCard({
    super.key,
    required this.child,
    this.blur = 20,
    this.opacity = 0.08,
    this.padding = const EdgeInsets.all(16),
    this.borderRadius = const BorderRadius.all(Radius.circular(16)),
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: opacity),
            borderRadius: borderRadius,
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.12),
              width: 1,
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}

/// Gradient border container
class GradientBorderCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final double borderWidth;

  const GradientBorderCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.borderWidth = 1.5,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: AppColors.gradientPrimary,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        margin: EdgeInsets.all(borderWidth),
        padding: padding,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14.5),
        ),
        child: child,
      ),
    );
  }
}

/// Shimmer loading placeholder
class ShimmerPlaceholder extends StatelessWidget {
  final double width;
  final double height;
  final BorderRadius? borderRadius;

  const ShimmerPlaceholder({
    super.key,
    this.width = double.infinity,
    this.height = 16,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.surfaceLighter,
        borderRadius: borderRadius ?? BorderRadius.circular(8),
      ),
    );
  }
}
