import 'package:get_storage/get_storage.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/services/analysis_service.dart';
import 'package:vital_step/services/force_reference_service.dart';
import 'package:vital_step/Model/force_reference.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vital_step/services/mode_service.dart';
import 'package:vital_step/services/patient_service.dart';
import 'package:vital_step/services/login_service.dart';
import 'package:vital_step/Model/patient_transfer_objects.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:vital_step/services/hubspot_sync_service.dart';

class TestResultViewModel extends BaseViewModel {
  late Future<Test?> testFuture;
  Test? test;
  final _apiCallsService = locator<ApiCallsService>();
  final _analysisService = locator<AnalysisService>();
  final _modeService = locator<ModeService>();
  final _patientService = locator<PatientService>();
  final _forceReferenceService = locator<ForceReferenceService>();
  final _loginService = locator<LoginService>();
  final _box = GetStorage();
  final _hubspotSyncService = HubspotSyncService();
  ForceReference? forceReference;

  /// GetStorage key that holds a Set of "patientId:testId" strings already
  /// dual-written, preventing re-writing the same test if the result screen is
  /// refreshed or revisited.
  static const String _dualWrittenKey = 'dual_written_test_ids';

  /// Temporary switch to keep trial values from being auto-synced to the patient
  /// record until a manual save action is implemented.
  static const bool _autoSyncPatientReadings = false;

  Future<Test?> initialise() async {
    testFuture = _apiCallsService.getLastTest();
    test = await testFuture;
    if (test != null) {
      // Trigger dual-write to patient Supabase (non-blocking)
      _handleDualWrite(test!);
      await _syncToHubspot(test!);
      await _loadForceReference(test!);
    }
    return test;
  }

  Future<void> _syncToHubspot(Test completedTest) async {
    try {
      final profile = await _patientService.getPatient(_modeService.activePatientId!);
      if (profile == null) return;

      final userId = await _loginService.getUserId();
      if (userId == null || userId.isEmpty) return;

      final accountProfile = await _patientService.getPatient(_modeService.activePatientId!);
      if (accountProfile == null) return;

      await _hubspotSyncService.syncAppContact(
        profile: Profile(name: accountProfile.name, phone: accountProfile.contact, dominantHand: null, countryCode: '', weight: 0, height: 0),
        test: completedTest,
        patientCode: accountProfile.patientCode,
      );
    } catch (_) {
      // Do not block the UI if HubSpot sync fails.
    }
  }

  Future<void> _loadForceReference(Test completedTest) async {
    // A reference needs demographic features. Those are available for the
    // active research patient, not for a generic host-mode test.
    if (!_modeService.isPatientMode || !_modeService.hasActivePatient) return;
    try {
      final patient =
          await _patientService.getPatient(_modeService.activePatientId!);
      if (patient == null) return;
      forceReference = await _forceReferenceService.getReference(
        patient: patient,
        hand: completedTest.hand,
        posture: completedTest.posture,
      );
      notifyListeners();
    } catch (_) {
      // Existing rule-based analysis remains the intentional fallback.
    }
  }

  /// Returns a composite key used to deduplicate dual-writes.
  /// Format: "<patientId>:<testId>"
  String _dualWriteKey(String patientId, int testId) => '$patientId:$testId';

  /// Whether this test has already been written to the patient Supabase DB.
  bool _alreadyDualWritten(String patientId, int testId) {
    final List<dynamic> written = (_box.read<List>(_dualWrittenKey) ?? []);
    return written.contains(_dualWriteKey(patientId, testId));
  }

  /// Marks this test as dual-written so subsequent calls are skipped.
  void _markDualWritten(String patientId, int testId) {
    final List<dynamic> written =
        List.from(_box.read<List>(_dualWrittenKey) ?? []);
    final key = _dualWriteKey(patientId, testId);
    if (!written.contains(key)) {
      written.add(key);
      // Keep the list from growing indefinitely — keep last 200 entries.
      if (written.length > 200) written.removeRange(0, written.length - 200);
      _box.write(_dualWrittenKey, written);
    }
  }

  /// Dual-write guard: saves a copy of the completed test to the Patient Supabase
  /// project when the app is in Patient Mode with an active patient selected.
  ///
  /// Guards:
  ///   • Only fires in Patient Mode with an active patient (Req 4.8).
  ///   • Deduplicates by patientId + testId so refreshing the result screen or
  ///     navigating back to it never writes the same record twice (data-leak fix).
  ///   • The test's createdAt must be recent (within the last 5 minutes) to
  ///     prevent a leftover host-account test from bleeding into a new patient.
  ///
  /// On failure, the reading is enqueued in the GetStorage retry queue and a
  /// non-blocking toast is shown (Req 4.5). Never throws.
  Future<void> _handleDualWrite(Test test) async {
    if (!_autoSyncPatientReadings) return;

    // Only write to patient Supabase if in Patient Mode with active patient
    if (!_modeService.isPatientMode || !_modeService.hasActivePatient) return;

    final patientId = _modeService.activePatientId!;

    // Deduplication: skip if this exact test was already saved for this patient.
    if (_alreadyDualWritten(patientId, test.id)) return;

    // Staleness guard: only save tests that were taken very recently (within
    // 5 minutes). This prevents an old host-account test from being injected
    // into a freshly-created patient who hasn't taken a test yet.
    final age = DateTime.now().difference(test.createdAt);
    if (age.inMinutes > 5) return;

    try {
      final hostUserId = await _loginService.getUserId() ?? '';
      final data = PatientReadingData(
        patientId: patientId,
        hostUserId: hostUserId,
        trial1: test.trial1,
        trial2: test.trial2,
        trial3: test.trial3,
        hand: test.hand,
        posture: test.posture,
        assessmentType: test.assestmentId.toString(),
        createdAt: test.createdAt,
      );

      await _patientService.saveReading(data);
      // Mark as written only after a successful save.
      _markDualWritten(patientId, test.id);
    } catch (e) {
      // Non-blocking: queue for retry, show toast
      try {
        final hostUserId = await _loginService.getUserId() ?? '';
        _patientService.enqueueReading(PatientReadingData(
          patientId: patientId,
          hostUserId: hostUserId,
          trial1: test.trial1,
          trial2: test.trial2,
          trial3: test.trial3,
          hand: test.hand,
          posture: test.posture,
          assessmentType: test.assestmentId.toString(),
          createdAt: test.createdAt,
        ));
        Fluttertoast.showToast(msg: 'Patient data queued for sync');
      } catch (_) {}
    }
  }

  String getAiInsight() {
    if (test == null) return "Loading analysis...";
    final reference = forceReference;
    if (reference != null) {
      final average = (double.parse(test!.trial1) +
              double.parse(test!.trial2) +
              double.parse(test!.trial3)) /
          3;
      final range =
          '${reference.p05Kg.toStringAsFixed(1)}–${reference.p95Kg.toStringAsFixed(1)} Kg';
      if (average < reference.p05Kg) {
        return 'Your ${average.toStringAsFixed(1)} Kg result is below the modelled reference range ($range) for this profile. This is a cohort comparison, not a diagnosis.';
      }
      if (average > reference.p95Kg) {
        return 'Your ${average.toStringAsFixed(1)} Kg result is above the modelled reference range ($range) for this profile.';
      }
      return 'Your ${average.toStringAsFixed(1)} Kg result is within the modelled reference range ($range) for this profile.';
    }
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
    final avg = (double.parse(test!.trial1) +
            double.parse(test!.trial2) +
            double.parse(test!.trial3)) /
        3;
    final message = "Vital Step Assessment Result:\n"
        "Date: ${getDate(test!.createdAt)}\n"
        "Posture: ${test!.posture}\n"
        "Hand: ${test!.hand}\n"
        "Average strength: ${avg.toStringAsFixed(2)} Kg\n"
        "AI Insight: ${getAiInsight()}";

    final url =
        Uri.parse("https://wa.me/?text=${Uri.encodeComponent(message)}");
    try {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (_) {}
  }

  Future<void> shareDetailedReport() async {
    if (test == null) return;
    final avg = (double.parse(test!.trial1) +
            double.parse(test!.trial2) +
            double.parse(test!.trial3)) /
        3;
    final message = "Vital Step - Detailed Specialist Report Request:\n"
        "Patient Assessment Date: ${getDate(test!.createdAt)}\n"
        "Symmetry: ${symmetryMetric.toStringAsFixed(1)}%\n"
        "Consistency: ${consistencyMetric.toStringAsFixed(1)}%\n"
        "Peak: ${peakMetric.toStringAsFixed(1)} Kg\n"
        "Average: ${avg.toStringAsFixed(2)} Kg\n"
        "Please review my latest metrics and provide guidance.";

    final url =
        Uri.parse("https://wa.me/?text=${Uri.encodeComponent(message)}");
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
    final variation = (([t1, t2, t3].reduce((a, b) => a > b ? a : b) -
            [t1, t2, t3].reduce((a, b) => a < b ? a : b)) /
        avg);
    return (1 - variation).clamp(0, 1) * 50;
  }

  double get symmetryMetric => _symmetryMetric;

  Future<void> calculateSymmetry() async {
    final Map<String, Test?> hands = await _apiCallsService.getHandsValues();
    if (hands["Left"] != null && hands["Right"] != null) {
      final lAvg = (double.parse(hands["Left"]!.trial1) +
              double.parse(hands["Left"]!.trial2) +
              double.parse(hands["Left"]!.trial3)) /
          3;
      final rAvg = (double.parse(hands["Right"]!.trial1) +
              double.parse(hands["Right"]!.trial2) +
              double.parse(hands["Right"]!.trial3)) /
          3;
      final diff = (lAvg - rAvg).abs();
      _symmetryMetric = (1 - (diff / ((lAvg + rAvg) / 2))).clamp(0, 1) * 50;
      notifyListeners();
    }
  }
}
