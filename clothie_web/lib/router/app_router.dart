import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:clothie_web/screens/splash_screen.dart';
import 'package:clothie_web/screens/register_screen.dart';
import 'package:clothie_web/screens/chat/chat_screen.dart';
import 'package:clothie_web/screens/professor_dashboard_page.dart';

/// Route arguments for ChatScreen
class ChatRouteArgs {
  final String sessionId;
  final String userName;
  final String? agentCodename; // cohort-only — null in non-cohort sessions

  ChatRouteArgs({
    required this.sessionId,
    required this.userName,
    this.agentCodename,
  });
}

/// Route arguments for ProfessorDashboardPage
class ProfessorDashboardRouteArgs {
  final String secretKey;

  ProfessorDashboardRouteArgs({required this.secretKey});
}

/// Centralized router configuration using go_router
final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    // Splash Screen (initial route)
    GoRoute(
      path: '/',
      name: 'splash',
      builder: (context, state) => const SplashScreen(),
    ),
    // Register Screen
    GoRoute(
      path: '/register',
      name: 'register',
      builder: (context, state) => const RegisterScreen(),
    ),
    // Chat Screen
    GoRoute(
      path: '/chat',
      name: 'chat',
      builder: (context, state) {
        final args = state.extra as ChatRouteArgs?;
        if (args == null) {
          // Fallback to register if no args provided
          return const RegisterScreen();
        }
        return ChatScreen(
          sessionId: args.sessionId,
          userName: args.userName,
          agentCodename: args.agentCodename,
        );
      },
    ),
    // Professor Dashboard Screen
    GoRoute(
      path: '/professor-dashboard',
      name: 'professor-dashboard',
      builder: (context, state) {
        final args = state.extra as ProfessorDashboardRouteArgs?;
        if (args == null || args.secretKey.isEmpty) {
          return const RegisterScreen();
        }
        return ProfessorDashboardPage(secretKey: args.secretKey);
      },
    ),
  ],
  errorBuilder: (context, state) => Scaffold(
    body: Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            '404',
            style: TextStyle(fontSize: 48, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Text('Page not found', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () => context.go('/'),
            child: const Text('Go Home'),
          ),
        ],
      ),
    ),
  ),
);
