import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/api_calls_service.dart';

class TestTakingViewModel extends BaseViewModel {
  final ApiCallsService _apiCallsService = locator<ApiCallsService>();
  final _dialogService = locator<DialogService>();
  void takeTest(Assessment assessment) async {
    setBusy(true);
    // we need to check the assessment queue.
    final assessmentQueue = await _apiCallsService.getAssessmentQueue(
        assessmentId: assessment.id.toString());
    // if the queue is empty, then give a popup and create a test
    if (assessmentQueue.isEmpty) {
      NavigationService().navigateToTestResultView();
      setBusy(false);
      return;
    } else {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: 'Complete the test',
          description: 'Please complete the test before viewing the results',
          data: {
            'title': 'Complete the test',
            'description':
                'Please complete the test before viewing the results',
            'buttonTitle': 'Ok',
          });
    }
    setBusy(false);
  }

  void cancelTest({required Assessment assessment}) async {
    try {
      if (assessment.queueId != null) {
        await _apiCallsService.cancelAssessment(queueId: assessment.queueId!);
      } else {
        int queueId = await _apiCallsService.getQueueId(assessment);
        await _apiCallsService.cancelAssessment(queueId: queueId);
      }
    } catch (e) {
      Fluttertoast.showToast(msg: 'Test not cancelled');
      NavigationService().clearStackAndShow(Routes.homeView,
          arguments: const HomeViewArguments(firstPage: 1));
    }
  }
}
