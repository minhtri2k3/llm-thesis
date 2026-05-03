import 'package:clothie_web/screens/professor_dashboard_page.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeProfessorApiService extends ApiService {
  final Duration delay;
  final Map<String, dynamic>? behaviourFunnel;
  final Object? behaviourError;
  final List<Map<String, dynamic>> tokenSessions;
  final Map<String, dynamic> demographics;

  _FakeProfessorApiService({
    this.delay = Duration.zero,
    this.behaviourFunnel,
    this.behaviourError,
    this.tokenSessions = const [],
    this.demographics = const {'by_gender': [], 'by_age_group': []},
  });

  @override
  Future<Map<String, dynamic>> getBehaviourFunnel(String secretKey) async {
    if (delay != Duration.zero) {
      await Future<void>.delayed(delay);
    }
    if (behaviourError != null) {
      throw behaviourError!;
    }
    return behaviourFunnel ??
        {
          'path_comparison': const [],
          'aggregate': const {
            'total_sessions': 0,
            'converted_sessions': 0,
            'overall_cr': 0.0,
            'avg_precision_at_k': 0.0,
          },
          'integrity': const {},
        };
  }

  @override
  Future<List<Map<String, dynamic>>> getTokenAnalytics(String secretKey) async {
    if (delay != Duration.zero) {
      await Future<void>.delayed(delay);
    }
    return tokenSessions;
  }

  @override
  Future<Map<String, dynamic>> getDemographics(String secretKey) async {
    if (delay != Duration.zero) {
      await Future<void>.delayed(delay);
    }
    return demographics;
  }
}

void main() {
  Widget wrap(Widget child) => MaterialApp(home: child);

  testWidgets('shows loading then empty state', (tester) async {
    final api = _FakeProfessorApiService(
      delay: const Duration(milliseconds: 40),
    );

    await tester.pumpWidget(
      wrap(ProfessorDashboardPage(secretKey: 'ok', apiService: api)),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pumpAndSettle();
    expect(find.text('No analytics data yet'), findsOneWidget);
  });

  testWidgets('shows unauthorized state for 403 access errors', (tester) async {
    final api = _FakeProfessorApiService(
      behaviourError: Exception('403: Incorrect access code'),
    );

    await tester.pumpWidget(
      wrap(ProfessorDashboardPage(secretKey: 'bad', apiService: api)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Access denied'), findsOneWidget);
    expect(find.text('Back to Register'), findsOneWidget);
  });

  testWidgets('shows error state for non-auth errors', (tester) async {
    final api = _FakeProfessorApiService(
      behaviourError: Exception('500: Server exploded'),
    );

    await tester.pumpWidget(
      wrap(ProfessorDashboardPage(secretKey: 'ok', apiService: api)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Unable to load analytics'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('renders comparison charts and integrity section with data', (
    tester,
  ) async {
    final api = _FakeProfessorApiService(
      behaviourFunnel: {
        'path_comparison': [
          {
            'path_mode': 'path1',
            'impressions': 100,
            'clicks': 50,
            'cart_adds': 20,
            'will_buy': 10,
            'orders': 8,
            'ctr': 0.5,
            'cart_rate': 0.4,
            'intent_rate': 0.5,
            'precision_at_k': 0.1,
            'invalid_segments': 0,
          },
          {
            'path_mode': 'path2',
            'impressions': 80,
            'clicks': 32,
            'cart_adds': 10,
            'will_buy': 3,
            'orders': 2,
            'ctr': 0.4,
            'cart_rate': 0.3125,
            'intent_rate': 0.3,
            'precision_at_k': 0.0375,
            'invalid_segments': 2,
          },
        ],
        'aggregate': {
          'total_sessions': 12,
          'converted_sessions': 4,
          'overall_cr': 0.333,
          'avg_precision_at_k': 0.12,
        },
        'integrity': {
          'valid': false,
          'invalid_sessions': 1,
          'issue_counts': {'path2:clicks_without_impressions': 1},
        },
      },
      tokenSessions: const [
        {
          'session_id': 'abc123456789xyz',
          'user_name': 'Alice',
          'model_name': 'gemini-2.5-flash',
          'total_tokens': 500,
        },
      ],
      demographics: const {
        'by_gender': [
          {'gender': 'female', 'avg_rating': 4.2, 'count': 6},
        ],
        'by_age_group': [
          {'age_group': '20-29', 'avg_rating': 4.1, 'count': 7},
        ],
      },
    );

    await tester.pumpWidget(
      wrap(ProfessorDashboardPage(secretKey: 'ok', apiService: api)),
    );
    await tester.pumpAndSettle();

    expect(find.text('PATH 1 vs PATH 2 Funnel Metrics'), findsOneWidget);
    expect(find.text('PATH 1 vs PATH 2 Rates'), findsOneWidget);
    expect(find.text('Integrity Signals'), findsOneWidget);
    expect(find.text('Invalid sessions: 1'), findsOneWidget);
  });
}
