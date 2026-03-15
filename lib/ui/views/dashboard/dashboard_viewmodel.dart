import 'dart:async';
import 'package:fl_chart/fl_chart.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/api_calls_service.dart';

class DashboardViewModel extends BaseViewModel {
  final _apiCallsService = locator<ApiCallsService>();

  List<Test> _allTests = [];

  // ── Left hand stats ──
  double leftCurrentWeek = 0;
  double leftLastWeek = 0;
  double leftAllTime = 0;
  double leftPeak = 0;
  int leftCount = 0;

  // ── Right hand stats ──
  double rightCurrentWeek = 0;
  double rightLastWeek = 0;
  double rightAllTime = 0;
  double rightPeak = 0;
  int rightCount = 0;

  // ── Posture breakdown (unique postures found in real data) ──
  Map<String, double> postureAverages = {};

  // ── Trend spots for chart ──
  List<FlSpot> leftSpots = [];
  List<FlSpot> rightSpots = [];

  int totalTests = 0;
  int thisWeekTests = 0;

  Timer? _pollingTimer;

  Future<void> init() async {
    setBusy(true);
    await refreshData();
    setBusy(false);
    _pollingTimer = Timer.periodic(const Duration(seconds: 15), (_) => refreshData());
  }

  Future<void> refreshData() async {
    try {
      _allTests = await _apiCallsService.getAllUserTests();
      _calculateStats();
      notifyListeners();
    } catch (_) {}
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  double _safe(String s) => double.tryParse(s) ?? 0.0;

  double _avg(Test t) => (_safe(t.trial1) + _safe(t.trial2) + _safe(t.trial3)) / 3;
  double _peak(Test t) => [_safe(t.trial1), _safe(t.trial2), _safe(t.trial3)]
      .reduce((a, b) => a > b ? a : b);

  void _calculateStats() {
    if (_allTests.isEmpty) return;

    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday - 1));
    final lastWeekStart = weekStart.subtract(const Duration(days: 7));

    final left = _allTests.where((t) => t.hand == 'Left').toList();
    final right = _allTests.where((t) => t.hand == 'Right').toList();

    // ── Left ──
    leftCount = left.length;
    if (left.isNotEmpty) {
      leftAllTime = left.map(_avg).reduce((a, b) => a + b) / left.length;
      leftPeak = left.map(_peak).reduce((a, b) => a > b ? a : b);

      final lcw = left.where((t) => t.createdAt.isAfter(weekStart)).toList();
      leftCurrentWeek = lcw.isEmpty ? 0 : lcw.map(_avg).reduce((a, b) => a + b) / lcw.length;

      final llw = left
          .where((t) => t.createdAt.isAfter(lastWeekStart) && t.createdAt.isBefore(weekStart))
          .toList();
      leftLastWeek = llw.isEmpty ? 0 : llw.map(_avg).reduce((a, b) => a + b) / llw.length;
    }

    // ── Right ──
    rightCount = right.length;
    if (right.isNotEmpty) {
      rightAllTime = right.map(_avg).reduce((a, b) => a + b) / right.length;
      rightPeak = right.map(_peak).reduce((a, b) => a > b ? a : b);

      final rcw = right.where((t) => t.createdAt.isAfter(weekStart)).toList();
      rightCurrentWeek = rcw.isEmpty ? 0 : rcw.map(_avg).reduce((a, b) => a + b) / rcw.length;

      final rlw = right
          .where((t) => t.createdAt.isAfter(lastWeekStart) && t.createdAt.isBefore(weekStart))
          .toList();
      rightLastWeek = rlw.isEmpty ? 0 : rlw.map(_avg).reduce((a, b) => a + b) / rlw.length;
    }

    // ── Posture breakdown (from real data) ──
    final Map<String, List<double>> postureMap = {};
    for (final t in _allTests) {
      postureMap.putIfAbsent(t.posture, () => []).add(_avg(t));
    }
    postureAverages = postureMap.map((k, v) =>
        MapEntry(k, v.reduce((a, b) => a + b) / v.length));

    // ── Trend sparklines (last 10) ──
    final recentLeft = left.length > 10 ? left.sublist(left.length - 10) : left;
    final recentRight = right.length > 10 ? right.sublist(right.length - 10) : right;
    leftSpots = recentLeft.asMap().entries.map((e) => FlSpot(e.key.toDouble(), _avg(e.value))).toList();
    rightSpots = recentRight.asMap().entries.map((e) => FlSpot(e.key.toDouble(), _avg(e.value))).toList();

    totalTests = _allTests.length;
    thisWeekTests = _allTests.where((t) => t.createdAt.isAfter(weekStart)).length;
  }

  bool get hasData => _allTests.isNotEmpty;
}
