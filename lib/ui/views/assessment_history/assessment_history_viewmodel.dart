import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/api_calls_service.dart';

class AssessmentHistoryViewModel extends BaseViewModel {
  List<Test>? tests;
  final _accountsService = locator<AccountsService>();
  final _apiCallsService = locator<ApiCallsService>();
  init({required int assessmentId, int? patientUserId}) async {
    tests = null;
    rebuildUi();
    tests = await _apiCallsService.getAllAssessmentTests(
        assessmentId: assessmentId);
    if (tests!.isEmpty) {
      rebuildUi();
      return;
    }
    tests!.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    rebuildUi();
  }

  String? dominantHand;

  String calculateAverage(Test test) {
    final double trial1 = double.parse(test.trial1);
    final double trial2 = double.parse(test.trial2);
    final double trial3 = double.parse(test.trial3);
    final double average = (trial1 + trial2 + trial3) / 3;
    return average.toStringAsFixed(2);
  }

  String getDate(DateTime string) {
    // dd - mm - yy
    return "${string.day} - ${string.month} - ${string.year}";
  }

  List<Test> getHandTests({required String hand, required bool isAscending}) {
    List<Test> handTests = [];
    try {
      for (var test in tests!) {
        if (test.hand == hand) {
          handTests.add(test);
        }
      }
      // we need to sort the handTest, in decreasing order of createdAt
      if (!isAscending) {
        handTests.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      } else {
        handTests.sort((a, b) => a.createdAt.compareTo(b.createdAt));
      }
    } catch (e) {
      print(e);
    }
    return handTests;
  }

  String getLatestTestAverage({required String hand}) {
    List<Test> handTests = getHandTests(hand: hand, isAscending: false);
    if (handTests.isEmpty) return "unavailable";
    final latestTest = handTests.first;
    return calculateAverage(latestTest);
  }

  String getLatestAverageDifference() {
    List<Test> rightHandTests = getHandTests(hand: "Right", isAscending: false);
    List<Test> leftHandTests = getHandTests(hand: "Left", isAscending: false);
    if (rightHandTests.isEmpty || leftHandTests.isEmpty) return "unavailable";
    final leftHandLatestTest = leftHandTests.first;
    final rightHandLatestTest = rightHandTests.first;
    final double leftHandAverage =
        double.parse(calculateAverage(leftHandLatestTest));
    final double rightHandAverage =
        double.parse(calculateAverage(rightHandLatestTest));
    final double difference = leftHandAverage - rightHandAverage;
    return difference.toStringAsFixed(2);
  }

  double getMaxAverageOfLastTest() {
    List<Test> rightHandTests = getHandTests(hand: "Right", isAscending: false);
    List<Test> leftHandTests = getHandTests(hand: "Left", isAscending: false);
    double leftHandAverage = 0;
    double rightHandAverage = 0;
    if (leftHandTests.isEmpty) {
      final rightHandLatestTest = rightHandTests.first;
      rightHandAverage = double.parse(calculateAverage(rightHandLatestTest));
      return rightHandAverage;
    }
    if (rightHandTests.isEmpty) {
      final leftHandLatestTest = leftHandTests.first;
      leftHandAverage = double.parse(calculateAverage(leftHandLatestTest));
      return leftHandAverage;
    }

    return leftHandAverage > rightHandAverage
        ? leftHandAverage
        : rightHandAverage;
  }

  double getMinAverageOfLastTest() {
    List<Test> rightHandTests = getHandTests(hand: "Right", isAscending: false);
    List<Test> leftHandTests = getHandTests(hand: "Left", isAscending: false);
    final leftHandLatestTest = leftHandTests.first;
    final rightHandLatestTest = rightHandTests.first;
    final double leftHandAverage =
        double.parse(calculateAverage(leftHandLatestTest));
    final double rightHandAverage =
        double.parse(calculateAverage(rightHandLatestTest));
    return leftHandAverage < rightHandAverage
        ? leftHandAverage
        : rightHandAverage;
  }

  final _accountService = locator<AccountsService>();
  getDominantHand({int? patientId}) async {
    final profile =
        await _accountService.getAccountDetails(patientUserId: patientId);
    dominantHand = profile.dominantHand;
    rebuildUi();
    return dominantHand;
  }

  Future<void> deleteTest({required int id, required int assessmentId}) async {
    await _apiCallsService.deleteTest(id: id);
    await init(assessmentId: assessmentId);
    rebuildUi();
  }

  void generatePDF({required int assessmentId}) async {
    final Profile profile = await _accountService.getAccountDetails();
    final List<Test> tests = await _apiCallsService.getAllAssessmentTests(
        assessmentId: assessmentId);
  }
}
