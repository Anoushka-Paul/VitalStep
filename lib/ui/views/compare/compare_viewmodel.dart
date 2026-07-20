import 'package:fl_chart/fl_chart.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/analysis_service.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/services/mode_service.dart';
import 'package:vital_step/services/patient_service.dart';

class CompareViewModel extends BaseViewModel {
  final _apiCallsService = locator<ApiCallsService>();
  final _analysisService = locator<AnalysisService>();
  final _accountsService = locator<AccountsService>();
  final _modeService = locator<ModeService>();
  final _patientService = locator<PatientService>();

  List<Test> _allTests = [];
  double leftAvg = 0.0;
  double rightAvg = 0.0;
  double leftPeak = 0.0;
  double rightPeak = 0.0;
  int leftCount = 0;
  int rightCount = 0;
  String dominantHand = '';
  CompareResult? compareResult;

  Future<void> init() async {
    setBusy(true);
    try {
      if (_modeService.isPatientMode && _modeService.hasActivePatient) {
        // Patient mode: load from Patient Supabase
        final readings =
            await _patientService.getReadings(_modeService.activePatientId!);
        _allTests = readings.map((r) => r.toTest()).toList();
        // Use the host's dominant hand setting (profile hasn't changed)
        final profile = await _accountsService.getAccountDetails();
        dominantHand = profile.dominantHand ?? 'Right';
      } else {
        // Host mode: use Digital Ocean API as before
        _allTests = await _apiCallsService.getAllUserTests();
        final profile = await _accountsService.getAccountDetails();
        dominantHand = profile.dominantHand ?? 'Right';
      }
      _compute();
    } catch (_) {}
    setBusy(false);
  }

  double _p(String? s) => double.tryParse(s ?? '0') ?? 0.0;
  double _testAvg(Test t) => (_p(t.trial1) + _p(t.trial2) + _p(t.trial3)) / 3;
  double _testPeak(Test t) {
    final vals = [_p(t.trial1), _p(t.trial2), _p(t.trial3)];
    return vals.reduce((a, b) => a > b ? a : b);
  }

  void _compute() {
    final leftTests = _allTests.where((t) => t.hand == 'Left').toList();
    final rightTests = _allTests.where((t) => t.hand == 'Right').toList();

    leftCount = leftTests.length;
    rightCount = rightTests.length;

    if (leftTests.isNotEmpty) {
      leftAvg =
          leftTests.map(_testAvg).reduce((a, b) => a + b) / leftTests.length;
      leftPeak = leftTests.map(_testPeak).reduce((a, b) => a > b ? a : b);
    }
    if (rightTests.isNotEmpty) {
      rightAvg =
          rightTests.map(_testAvg).reduce((a, b) => a + b) / rightTests.length;
      rightPeak = rightTests.map(_testPeak).reduce((a, b) => a > b ? a : b);
    }

    compareResult = _analysisService.compareHandsStructured(
        leftAvg, rightAvg, dominantHand);
  }

  List<FlSpot> trendData(String hand) {
    final tests = _allTests.where((t) => t.hand == hand).toList();
    final recent = tests.length > 8 ? tests.sublist(tests.length - 8) : tests;
    return recent
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), _testAvg(e.value)))
        .toList();
  }

  bool get hasData => _allTests.isNotEmpty;
}
