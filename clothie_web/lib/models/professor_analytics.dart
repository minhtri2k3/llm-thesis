class ProfessorAnalyticsViewModel {
  final int totalSessions;
  final int convertedSessions;
  final double overallConversionRate;
  final double avgPrecisionAtK;
  final int grandTotalTokens;
  final List<PathMetricDatum> funnelMetrics;
  final List<PathRateDatum> rateMetrics;
  final List<PathIntegritySummary> pathIntegrity;
  final bool integrityValid;
  final int invalidSessions;
  final List<IntegrityIssueCount> issueCounts;
  final bool hasIntegritySummary;
  final List<DemographicSummary> genderSummaries;
  final List<DemographicSummary> ageSummaries;
  final List<TokenSessionSummary> topTokenSessions;

  const ProfessorAnalyticsViewModel({
    required this.totalSessions,
    required this.convertedSessions,
    required this.overallConversionRate,
    required this.avgPrecisionAtK,
    required this.grandTotalTokens,
    required this.funnelMetrics,
    required this.rateMetrics,
    required this.pathIntegrity,
    required this.integrityValid,
    required this.invalidSessions,
    required this.issueCounts,
    required this.hasIntegritySummary,
    required this.genderSummaries,
    required this.ageSummaries,
    required this.topTokenSessions,
  });

  bool get isEmpty =>
      totalSessions == 0 &&
      grandTotalTokens == 0 &&
      topTokenSessions.isEmpty &&
      funnelMetrics.every((m) => m.path1 == 0 && m.path2 == 0);

  int get averageTokensPerSession =>
      totalSessions == 0 ? 0 : (grandTotalTokens / totalSessions).round();

  factory ProfessorAnalyticsViewModel.fromPayloads({
    required Map<String, dynamic> behaviourFunnel,
    required List<Map<String, dynamic>> tokenSessions,
    required Map<String, dynamic> demographics,
  }) {
    final aggregate =
        (behaviourFunnel['aggregate'] as Map?)?.cast<String, dynamic>() ?? {};
    final integrity =
        (behaviourFunnel['integrity'] as Map?)?.cast<String, dynamic>() ?? {};

    final pathComparison = (behaviourFunnel['path_comparison'] as List? ?? [])
        .whereType<Map>()
        .map((row) => row.cast<String, dynamic>())
        .toList();

    final canonicalPaths = _buildCanonicalPaths(pathComparison);
    final path1 = canonicalPaths['path1']!;
    final path2 = canonicalPaths['path2']!;

    final issueCountsMap =
        (integrity['issue_counts'] as Map?)?.cast<String, dynamic>() ?? {};
    final issueCounts =
        issueCountsMap.entries
            .map(
              (entry) => IntegrityIssueCount(
                issue: entry.key,
                count: _asInt(entry.value),
              ),
            )
            .where((entry) => entry.count > 0)
            .toList()
          ..sort((a, b) => b.count.compareTo(a.count));

    final hasIntegritySummary =
        integrity.containsKey('invalid_sessions') ||
        integrity.containsKey('issue_counts');

    final sortedTokens =
        tokenSessions
            .map(
              (row) => TokenSessionSummary(
                sessionId: (row['session_id'] as String?) ?? '',
                userName: (row['user_name'] as String?) ?? 'Anonymous',
                modelName: (row['model_name'] as String?) ?? 'unknown',
                totalTokens: _asInt(row['total_tokens']),
              ),
            )
            .toList()
          ..sort((a, b) => b.totalTokens.compareTo(a.totalTokens));

    final byGender = (demographics['by_gender'] as List? ?? [])
        .whereType<Map>()
        .map((row) => row.cast<String, dynamic>())
        .map(
          (row) => DemographicSummary(
            label: _normalizeGender((row['gender'] as String?) ?? 'unknown'),
            avgRating: _asDouble(row['avg_rating']),
            count: _asInt(row['count']),
          ),
        )
        .toList();

    final byAge = (demographics['by_age_group'] as List? ?? [])
        .whereType<Map>()
        .map((row) => row.cast<String, dynamic>())
        .map(
          (row) => DemographicSummary(
            label: (row['age_group'] as String?) ?? 'Unknown',
            avgRating: _asDouble(row['avg_rating']),
            count: _asInt(row['count']),
          ),
        )
        .toList();

    return ProfessorAnalyticsViewModel(
      totalSessions: _asInt(aggregate['total_sessions']),
      convertedSessions: _asInt(aggregate['converted_sessions']),
      overallConversionRate: _asDouble(aggregate['overall_cr']),
      avgPrecisionAtK: _asDouble(aggregate['avg_precision_at_k']),
      grandTotalTokens: sortedTokens.fold<int>(
        0,
        (sum, item) => sum + item.totalTokens,
      ),
      funnelMetrics: [
        PathMetricDatum(
          label: 'Impressions',
          path1: _asInt(path1['impressions']),
          path2: _asInt(path2['impressions']),
        ),
        PathMetricDatum(
          label: 'Clicks',
          path1: _asInt(path1['clicks']),
          path2: _asInt(path2['clicks']),
        ),
        PathMetricDatum(
          label: 'Cart Adds',
          path1: _asInt(path1['cart_adds']),
          path2: _asInt(path2['cart_adds']),
        ),
        PathMetricDatum(
          label: 'Will Buy',
          path1: _asInt(path1['will_buy']),
          path2: _asInt(path2['will_buy']),
        ),
        PathMetricDatum(
          label: 'Orders',
          path1: _asInt(path1['orders']),
          path2: _asInt(path2['orders']),
        ),
      ],
      rateMetrics: [
        PathRateDatum(
          label: 'CTR',
          path1: _asDouble(path1['ctr']),
          path2: _asDouble(path2['ctr']),
        ),
        PathRateDatum(
          label: 'Cart Rate',
          path1: _asDouble(path1['cart_rate']),
          path2: _asDouble(path2['cart_rate']),
        ),
        PathRateDatum(
          label: 'Intent Rate',
          path1: _asDouble(path1['intent_rate']),
          path2: _asDouble(path2['intent_rate']),
        ),
        PathRateDatum(
          label: 'Precision@K',
          path1: _asDouble(path1['precision_at_k']),
          path2: _asDouble(path2['precision_at_k']),
        ),
      ],
      pathIntegrity: [
        PathIntegritySummary(
          pathMode: 'path1',
          invalidSegments: _asInt(path1['invalid_segments']),
          isValid: _asInt(path1['invalid_segments']) == 0,
        ),
        PathIntegritySummary(
          pathMode: 'path2',
          invalidSegments: _asInt(path2['invalid_segments']),
          isValid: _asInt(path2['invalid_segments']) == 0,
        ),
      ],
      integrityValid: (integrity['valid'] as bool?) ?? true,
      invalidSessions: _asInt(integrity['invalid_sessions']),
      issueCounts: issueCounts,
      hasIntegritySummary: hasIntegritySummary,
      genderSummaries: byGender,
      ageSummaries: byAge,
      topTokenSessions: sortedTokens.take(6).toList(),
    );
  }

  static Map<String, Map<String, dynamic>> _buildCanonicalPaths(
    List<Map<String, dynamic>> raw,
  ) {
    final map = <String, Map<String, dynamic>>{};
    for (final row in raw) {
      final mode = ((row['path_mode'] as String?) ?? '').toLowerCase().trim();
      if (mode == 'path1' || mode == 'path2') {
        map[mode] = row;
      }
    }

    Map<String, dynamic> zeroPath(String mode) => {
      'path_mode': mode,
      'impressions': 0,
      'clicks': 0,
      'cart_adds': 0,
      'will_buy': 0,
      'orders': 0,
      'ctr': 0.0,
      'cart_rate': 0.0,
      'intent_rate': 0.0,
      'precision_at_k': 0.0,
      'invalid_segments': 0,
    };

    return {
      'path1': map['path1'] ?? zeroPath('path1'),
      'path2': map['path2'] ?? zeroPath('path2'),
    };
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static double _asDouble(dynamic value) {
    if (value is double) return value;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }

  static String _normalizeGender(String raw) {
    switch (raw.toLowerCase()) {
      case 'male':
        return 'Male';
      case 'female':
        return 'Female';
      default:
        return 'Unknown';
    }
  }
}

class PathMetricDatum {
  final String label;
  final int path1;
  final int path2;

  const PathMetricDatum({
    required this.label,
    required this.path1,
    required this.path2,
  });
}

class PathRateDatum {
  final String label;
  final double path1;
  final double path2;

  const PathRateDatum({
    required this.label,
    required this.path1,
    required this.path2,
  });
}

class PathIntegritySummary {
  final String pathMode;
  final int invalidSegments;
  final bool isValid;

  const PathIntegritySummary({
    required this.pathMode,
    required this.invalidSegments,
    required this.isValid,
  });
}

class IntegrityIssueCount {
  final String issue;
  final int count;

  const IntegrityIssueCount({required this.issue, required this.count});
}

class TokenSessionSummary {
  final String sessionId;
  final String userName;
  final String modelName;
  final int totalTokens;

  const TokenSessionSummary({
    required this.sessionId,
    required this.userName,
    required this.modelName,
    required this.totalTokens,
  });
}

class DemographicSummary {
  final String label;
  final double avgRating;
  final int count;

  const DemographicSummary({
    required this.label,
    required this.avgRating,
    required this.count,
  });
}
