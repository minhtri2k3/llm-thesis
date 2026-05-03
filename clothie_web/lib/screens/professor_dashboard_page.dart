import 'package:clothie_web/models/professor_analytics.dart';
import 'package:clothie_web/services/api_service.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

class ProfessorDashboardPage extends StatefulWidget {
  final String secretKey;
  final ApiService? apiService;

  const ProfessorDashboardPage({
    super.key,
    required this.secretKey,
    this.apiService,
  });

  @override
  State<ProfessorDashboardPage> createState() => _ProfessorDashboardPageState();
}

class _ProfessorDashboardPageState extends State<ProfessorDashboardPage> {
  late final ApiService _api;
  late final bool _ownsApi;

  ProfessorAnalyticsViewModel? _viewModel;
  bool _loading = true;
  bool _unauthorized = false;
  String? _error;
  bool _showPath1 = true;
  bool _showPath2 = true;

  @override
  void initState() {
    super.initState();
    _ownsApi = widget.apiService == null;
    _api = widget.apiService ?? ApiService();
    _load();
  }

  @override
  void dispose() {
    if (_ownsApi) {
      _api.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _unauthorized = false;
    });

    try {
      final behaviourFunnel = await _api.getBehaviourFunnel(widget.secretKey);
      final tokenSessions = await _api.getTokenAnalytics(widget.secretKey);
      final demographics = await _api.getDemographics(widget.secretKey);

      if (!mounted) return;
      setState(() {
        _viewModel = ProfessorAnalyticsViewModel.fromPayloads(
          behaviourFunnel: behaviourFunnel,
          tokenSessions: tokenSessions,
          demographics: demographics,
        );
      });
    } catch (e) {
      if (!mounted) return;
      final message = e.toString();
      setState(() {
        if (message.contains('403')) {
          _unauthorized = true;
        } else {
          _error = message;
        }
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Professor Analytics Dashboard',
          style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh analytics',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(child: _buildBody(context)),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_unauthorized) {
      return _CenteredStateCard(
        icon: Icons.lock_outline_rounded,
        title: 'Access denied',
        message:
            'Your professor access key is invalid or expired. Please unlock again from Register.',
        primaryAction: ElevatedButton(
          onPressed: () => context.go('/register'),
          child: const Text('Back to Register'),
        ),
      );
    }

    if (_error != null) {
      return _CenteredStateCard(
        icon: Icons.error_outline_rounded,
        title: 'Unable to load analytics',
        message: _error!,
        primaryAction: ElevatedButton(
          onPressed: _load,
          child: const Text('Retry'),
        ),
      );
    }

    final vm = _viewModel;
    if (vm == null || vm.isEmpty) {
      return _CenteredStateCard(
        icon: Icons.insert_chart_outlined_rounded,
        title: 'No analytics data yet',
        message:
            'No professor analytics are available at the moment. Once user sessions exist, charts will appear here.',
        primaryAction: OutlinedButton(
          onPressed: _load,
          child: const Text('Refresh'),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final desktop = constraints.maxWidth >= 1100;
        final chartHeight = constraints.maxWidth >= 1400 ? 360.0 : 300.0;
        return SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1400),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSummaryCards(vm),
                  const SizedBox(height: 20),
                  _buildPathLegendControls(),
                  const SizedBox(height: 12),
                  if (desktop)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: _buildFunnelChartCard(vm, chartHeight)),
                        const SizedBox(width: 16),
                        Expanded(child: _buildRateChartCard(vm, chartHeight)),
                      ],
                    )
                  else ...[
                    _buildFunnelChartCard(vm, chartHeight),
                    const SizedBox(height: 16),
                    _buildRateChartCard(vm, chartHeight),
                  ],
                  const SizedBox(height: 16),
                  _buildIntegrityCard(vm),
                  const SizedBox(height: 16),
                  if (desktop)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: _buildTokenSessionCard(vm)),
                        const SizedBox(width: 16),
                        Expanded(child: _buildDemographicsCard(vm)),
                      ],
                    )
                  else ...[
                    _buildTokenSessionCard(vm),
                    const SizedBox(height: 16),
                    _buildDemographicsCard(vm),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildSummaryCards(ProfessorAnalyticsViewModel vm) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _SummaryCard(
          title: 'Total Sessions',
          value: _formatInt(vm.totalSessions),
          subtitle: 'Tracked sessions',
          icon: Icons.groups_rounded,
        ),
        _SummaryCard(
          title: 'Converted Sessions',
          value: _formatInt(vm.convertedSessions),
          subtitle: _toPercent(vm.overallConversionRate),
          icon: Icons.shopping_bag_outlined,
        ),
        _SummaryCard(
          title: 'Total Tokens',
          value: _formatInt(vm.grandTotalTokens),
          subtitle: 'Avg ${_formatInt(vm.averageTokensPerSession)} / session',
          icon: Icons.memory_rounded,
        ),
        _SummaryCard(
          title: 'Avg Precision@K',
          value: _toPercent(vm.avgPrecisionAtK),
          subtitle: 'Cross-path quality',
          icon: Icons.auto_graph_rounded,
        ),
      ],
    );
  }

  Widget _buildPathLegendControls() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        Text(
          'Path series visibility:',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.w600,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.8),
          ),
        ),
        FilterChip(
          selectedColor: const Color(0xFF3B82F6).withOpacity(0.16),
          label: const Text('PATH 1'),
          selected: _showPath1,
          onSelected: (value) => setState(() => _showPath1 = value),
        ),
        FilterChip(
          selectedColor: const Color(0xFFF97316).withOpacity(0.16),
          label: const Text('PATH 2'),
          selected: _showPath2,
          onSelected: (value) => setState(() => _showPath2 = value),
        ),
      ],
    );
  }

  Widget _buildFunnelChartCard(ProfessorAnalyticsViewModel vm, double height) {
    return _SectionCard(
      title: 'PATH 1 vs PATH 2 Funnel Metrics',
      child: _ChartGuard(
        fallback: _buildFunnelFallbackTable(vm),
        builder: () {
          final maxValue = vm.funnelMetrics.fold<int>(
            0,
            (max, row) => [
              max,
              if (_showPath1) row.path1,
              if (_showPath2) row.path2,
            ].reduce((a, b) => a > b ? a : b),
          );
          final maxY = maxValue > 0 ? (maxValue * 1.2) : 1;

          return SizedBox(
            height: height,
            child: BarChart(
              BarChartData(
                maxY: maxY.toDouble(),
                alignment: BarChartAlignment.spaceAround,
                barTouchData: _countTooltipData(vm),
                gridData: const FlGridData(show: true),
                titlesData: FlTitlesData(
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        final idx = value.toInt();
                        if (idx < 0 || idx >= vm.funnelMetrics.length) {
                          return const SizedBox.shrink();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            vm.funnelMetrics[idx].label,
                            style: GoogleFonts.outfit(fontSize: 11),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                barGroups: [
                  for (var i = 0; i < vm.funnelMetrics.length; i++)
                    BarChartGroupData(
                      x: i,
                      barsSpace: 4,
                      barRods: [
                        if (_showPath1)
                          BarChartRodData(
                            toY: vm.funnelMetrics[i].path1.toDouble(),
                            width: 16,
                            color: const Color(0xFF3B82F6),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        if (_showPath2)
                          BarChartRodData(
                            toY: vm.funnelMetrics[i].path2.toDouble(),
                            width: 16,
                            color: const Color(0xFFF97316),
                            borderRadius: BorderRadius.circular(4),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildRateChartCard(ProfessorAnalyticsViewModel vm, double height) {
    return _SectionCard(
      title: 'PATH 1 vs PATH 2 Rates',
      child: _ChartGuard(
        fallback: _buildRateFallbackTable(vm),
        builder: () {
          final maxRate = vm.rateMetrics.fold<double>(
            0,
            (max, row) => [
              max,
              if (_showPath1) row.path1,
              if (_showPath2) row.path2,
            ].reduce((a, b) => a > b ? a : b),
          );
          final maxY = maxRate > 0 ? ((maxRate * 100) * 1.2) : 1.0;

          return SizedBox(
            height: height,
            child: BarChart(
              BarChartData(
                maxY: maxY,
                alignment: BarChartAlignment.spaceAround,
                barTouchData: _rateTooltipData(vm),
                gridData: const FlGridData(show: true),
                titlesData: FlTitlesData(
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 48,
                      getTitlesWidget: (value, meta) {
                        return Text(
                          '${value.toInt()}%',
                          style: GoogleFonts.outfit(fontSize: 10),
                        );
                      },
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        final idx = value.toInt();
                        if (idx < 0 || idx >= vm.rateMetrics.length) {
                          return const SizedBox.shrink();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            vm.rateMetrics[idx].label,
                            style: GoogleFonts.outfit(fontSize: 11),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                barGroups: [
                  for (var i = 0; i < vm.rateMetrics.length; i++)
                    BarChartGroupData(
                      x: i,
                      barsSpace: 4,
                      barRods: [
                        if (_showPath1)
                          BarChartRodData(
                            toY: vm.rateMetrics[i].path1 * 100,
                            width: 16,
                            color: const Color(0xFF3B82F6),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        if (_showPath2)
                          BarChartRodData(
                            toY: vm.rateMetrics[i].path2 * 100,
                            width: 16,
                            color: const Color(0xFFF97316),
                            borderRadius: BorderRadius.circular(4),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  BarTouchData _countTooltipData(ProfessorAnalyticsViewModel vm) {
    return BarTouchData(
      enabled: true,
      touchTooltipData: BarTouchTooltipData(
        tooltipRoundedRadius: 8,
        getTooltipItem: (group, groupIndex, rod, rodIndex) {
          final metric = vm.funnelMetrics[group.x.toInt()];
          final pathLabel = _pathLabelFromRodIndex(rodIndex);
          return BarTooltipItem(
            '$pathLabel\n${metric.label}: ${_formatInt(rod.toY.toInt())}',
            const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
          );
        },
      ),
    );
  }

  BarTouchData _rateTooltipData(ProfessorAnalyticsViewModel vm) {
    return BarTouchData(
      enabled: true,
      touchTooltipData: BarTouchTooltipData(
        tooltipRoundedRadius: 8,
        getTooltipItem: (group, groupIndex, rod, rodIndex) {
          final metric = vm.rateMetrics[group.x.toInt()];
          final pathLabel = _pathLabelFromRodIndex(rodIndex);
          return BarTooltipItem(
            '$pathLabel\n${metric.label}: ${rod.toY.toStringAsFixed(1)}%',
            const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
          );
        },
      ),
    );
  }

  String _pathLabelFromRodIndex(int rodIndex) {
    if (_showPath1 && _showPath2) {
      return rodIndex == 0 ? 'PATH 1' : 'PATH 2';
    }
    return _showPath1 ? 'PATH 1' : 'PATH 2';
  }

  Widget _buildFunnelFallbackTable(ProfessorAnalyticsViewModel vm) {
    return _FallbackTable(
      title: 'Fallback Summary (counts)',
      columns: const ['Metric', 'PATH 1', 'PATH 2'],
      rows: vm.funnelMetrics
          .map(
            (row) => [row.label, _formatInt(row.path1), _formatInt(row.path2)],
          )
          .toList(),
    );
  }

  Widget _buildRateFallbackTable(ProfessorAnalyticsViewModel vm) {
    return _FallbackTable(
      title: 'Fallback Summary (rates)',
      columns: const ['Metric', 'PATH 1', 'PATH 2'],
      rows: vm.rateMetrics
          .map(
            (row) => [row.label, _toPercent(row.path1), _toPercent(row.path2)],
          )
          .toList(),
    );
  }

  Widget _buildIntegrityCard(ProfessorAnalyticsViewModel vm) {
    return _SectionCard(
      title: 'Integrity Signals',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final path in vm.pathIntegrity)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: path.isValid
                        ? const Color(0xFF16A34A).withOpacity(0.12)
                        : const Color(0xFFDC2626).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${path.pathMode.toUpperCase()}: ${path.isValid ? 'Valid' : '${path.invalidSegments} invalid segment(s)'}',
                    style: GoogleFonts.outfit(
                      fontWeight: FontWeight.w600,
                      color: path.isValid
                          ? const Color(0xFF15803D)
                          : const Color(0xFFB91C1C),
                    ),
                  ),
                ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: vm.integrityValid
                      ? const Color(0xFF16A34A).withOpacity(0.12)
                      : const Color(0xFFF59E0B).withOpacity(0.16),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'Invalid sessions: ${_formatInt(vm.invalidSessions)}',
                  style: GoogleFonts.outfit(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (!vm.hasIntegritySummary)
            Text(
              'Integrity details unavailable from API payload.',
              style: GoogleFonts.outfit(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
            )
          else if (vm.issueCounts.isEmpty)
            Text(
              'No integrity issues were detected in the current dataset.',
              style: GoogleFonts.outfit(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: vm.issueCounts
                  .take(10)
                  .map(
                    (entry) => Chip(
                      label: Text('${entry.issue}: ${entry.count}'),
                      avatar: const Icon(Icons.warning_amber_rounded, size: 16),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildTokenSessionCard(ProfessorAnalyticsViewModel vm) {
    return _SectionCard(
      title: 'Top Token Sessions',
      child: vm.topTokenSessions.isEmpty
          ? Text(
              'No token sessions available.',
              style: GoogleFonts.outfit(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
            )
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: const [
                  DataColumn(label: Text('Session')),
                  DataColumn(label: Text('User')),
                  DataColumn(label: Text('Model')),
                  DataColumn(label: Text('Tokens')),
                ],
                rows: vm.topTokenSessions
                    .map(
                      (row) => DataRow(
                        cells: [
                          DataCell(Text(_shortSession(row.sessionId))),
                          DataCell(Text(row.userName)),
                          DataCell(Text(row.modelName)),
                          DataCell(Text(_formatInt(row.totalTokens))),
                        ],
                      ),
                    )
                    .toList(),
              ),
            ),
    );
  }

  Widget _buildDemographicsCard(ProfessorAnalyticsViewModel vm) {
    Widget summaryList(List<DemographicSummary> rows) {
      if (rows.isEmpty) {
        return Text(
          'N/A',
          style: GoogleFonts.outfit(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
        );
      }
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: rows
            .map(
              (row) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  '${row.label}: ${row.avgRating.toStringAsFixed(1)} ⭐ (${row.count})',
                  style: GoogleFonts.outfit(fontSize: 13),
                ),
              ),
            )
            .toList(),
      );
    }

    return _SectionCard(
      title: 'Demographics Snapshot',
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Gender',
                  style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                summaryList(vm.genderSummaries),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Age Group',
                  style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                summaryList(vm.ageSummaries),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _shortSession(String sessionId) {
    if (sessionId.length <= 12) return sessionId;
    return '${sessionId.substring(0, 12)}…';
  }

  String _formatInt(int value) {
    final s = value.toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) {
        buf.write(',');
      }
      buf.write(s[i]);
    }
    return buf.toString();
  }

  String _toPercent(double value) => '${(value * 100).toStringAsFixed(1)}%';
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _SectionCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withOpacity(0.75),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Theme.of(context).colorScheme.secondary.withOpacity(0.16),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.outfit(
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;
  final IconData icon;

  const _SummaryCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withOpacity(0.75),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Theme.of(context).colorScheme.secondary.withOpacity(0.16),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                icon,
                size: 18,
                color: Theme.of(context).colorScheme.secondary,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.outfit(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: GoogleFonts.outfit(
              fontSize: 22,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: GoogleFonts.outfit(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _FallbackTable extends StatelessWidget {
  final String title;
  final List<String> columns;
  final List<List<String>> rows;

  const _FallbackTable({
    required this.title,
    required this.columns,
    required this.rows,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: GoogleFonts.outfit(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.85),
          ),
        ),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columns: columns
                .map((label) => DataColumn(label: Text(label)))
                .toList(),
            rows: rows
                .map(
                  (row) => DataRow(
                    cells: row.map((value) => DataCell(Text(value))).toList(),
                  ),
                )
                .toList(),
          ),
        ),
      ],
    );
  }
}

class _CenteredStateCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final Widget primaryAction;

  const _CenteredStateCard({
    required this.icon,
    required this.title,
    required this.message,
    required this.primaryAction,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: _SectionCard(
            title: title,
            child: Column(
              children: [
                Icon(
                  icon,
                  size: 42,
                  color: Theme.of(context).colorScheme.secondary,
                ),
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.outfit(
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withOpacity(0.8),
                  ),
                ),
                const SizedBox(height: 16),
                primaryAction,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ChartGuard extends StatelessWidget {
  final Widget Function() builder;
  final Widget fallback;

  const _ChartGuard({required this.builder, required this.fallback});

  @override
  Widget build(BuildContext context) {
    try {
      return builder();
    } catch (_) {
      return fallback;
    }
  }
}
