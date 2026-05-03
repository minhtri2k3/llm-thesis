import 'package:clothie_web/models/professor_analytics.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('maps missing PATH 2 and absent integrity fields safely', () {
    final vm = ProfessorAnalyticsViewModel.fromPayloads(
      behaviourFunnel: {
        'path_comparison': [
          {
            'path_mode': 'path1',
            'impressions': 10,
            'clicks': 5,
            'cart_adds': 2,
            'will_buy': 1,
            'orders': 1,
            'ctr': 0.5,
            'cart_rate': 0.4,
            'intent_rate': 0.5,
            'precision_at_k': 0.1,
            'invalid_segments': 0,
          },
        ],
        'aggregate': {
          'total_sessions': 4,
          'converted_sessions': 1,
          'overall_cr': 0.25,
          'avg_precision_at_k': 0.1,
        },
      },
      tokenSessions: [],
      demographics: const {'by_gender': [], 'by_age_group': []},
    );

    final impressions = vm.funnelMetrics.firstWhere(
      (row) => row.label == 'Impressions',
    );
    expect(impressions.path1, 10);
    expect(impressions.path2, 0);
    expect(vm.hasIntegritySummary, isFalse);
    expect(
      vm.pathIntegrity.firstWhere((row) => row.pathMode == 'path2').isValid,
      isTrue,
    );
  });
}
