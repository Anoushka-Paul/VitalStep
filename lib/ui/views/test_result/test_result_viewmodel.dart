import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/services/analysis_service.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vital_step/ui/widgets/common/analysis_radar_chart.dart';

class TestResultViewModel extends BaseViewModel {
  late Future<Test?> testFuture;
  Test? test;
  final _apiCallsService = locator<ApiCallsService>();
  final _analysisService = locator<AnalysisService>();

  Future<Test?> initialise() async {
    testFuture = _apiCallsService.getLastTest();
    test = await testFuture;
    return test;
  }

  String getAiInsight() {
    if (test == null) return "Loading analysis...";
    return _analysisService.analyzeTrials(test!);
  }

  List<String> getRecoveryTips() {
    if (test == null) return [];
    return _analysisService.getRecoveryTips(test!);
  }

  String getDate(DateTime createdAt) {
    return "${createdAt.day}/${createdAt.month}/${createdAt.year}";
  }

  String getTime(DateTime createdAt) {
    return "${createdAt.hour}:${createdAt.minute}";
  }

  Future<void> shareOnWhatsApp() async {
    if (test == null) return;
    final avg = (double.parse(test!.trial1) + double.parse(test!.trial2) + double.parse(test!.trial3)) / 3;
    final message = "Vital Step Assessment Result:\n"
        "Date: ${getDate(test!.createdAt)}\n"
        "Posture: ${test!.posture}\n"
        "Hand: ${test!.hand}\n"
        "Average strength: ${avg.toStringAsFixed(2)} Kg\n"
        "AI Insight: ${getAiInsight()}";
    
    final url = Uri.parse("https://wa.me/?text=${Uri.encodeComponent(message)}");
    try {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (_) {}
  }

  Future<void> shareDetailedReport() async {
    if (test == null) return;
    final avg = (double.parse(test!.trial1) + double.parse(test!.trial2) + double.parse(test!.trial3)) / 3;
    final message = "Vital Step - Detailed Specialist Report Request:\n"
        "Patient Assessment Date: ${getDate(test!.createdAt)}\n"
        "Symmetry: ${symmetryMetric.toStringAsFixed(1)}%\n"
        "Consistency: ${consistencyMetric.toStringAsFixed(1)}%\n"
        "Peak: ${peakMetric.toStringAsFixed(1)} Kg\n"
        "Average: ${avg.toStringAsFixed(2)} Kg\n"
        "Please review my latest metrics and provide guidance.";
    
    final url = Uri.parse("https://wa.me/?text=${Uri.encodeComponent(message)}");
    try {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (_) {}
  }

  double _symmetryMetric = 30.0;
  double get peakMetric => test != null ? double.parse(test!.trial1) : 0;
  double get consistencyMetric {
     if (test == null) return 0;
     final t1 = double.parse(test!.trial1);
     final t2 = double.parse(test!.trial2);
     final t3 = double.parse(test!.trial3);
     final avg = (t1 + t2 + t3) / 3;
     final variation = (([t1, t2, t3].reduce((a, b) => a > b ? a : b) - [t1, t2, t3].reduce((a, b) => a < b ? a : b)) / avg);
     return (1 - variation).clamp(0, 1) * 50; 
  }
  double get symmetryMetric => _symmetryMetric;

  Future<void> calculateSymmetry() async {
    final Map<String, Test?> hands = await _apiCallsService.getHandsValues();
    if (hands["Left"] != null && hands["Right"] != null) {
      final lAvg = (double.parse(hands["Left"]!.trial1) + double.parse(hands["Left"]!.trial2) + double.parse(hands["Left"]!.trial3)) / 3;
      final rAvg = (double.parse(hands["Right"]!.trial1) + double.parse(hands["Right"]!.trial2) + double.parse(hands["Right"]!.trial3)) / 3;
      final diff = (lAvg - rAvg).abs();
      _symmetryMetric = (1 - (diff / ((lAvg + rAvg) / 2))).clamp(0, 1) * 50;
      notifyListeners();
    }
  }
}
