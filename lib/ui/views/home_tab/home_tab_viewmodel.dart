import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/accounts.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.logger.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/services/notifications_service.dart';

class HomeTabViewModel extends BaseViewModel {
  final _apiCallsService = locator<ApiCallsService>();
  final _logger = getLogger("HomeTabViewModel");
  final _accountService = locator<AccountsService>();
  Profile? profile;
  String rightHandValue = "";
  String leftHandValue = "";
  bool takeTestToGetHandAnalysis = false;

  Future<void> init() async {
    profile = await _accountService.getAccountDetails();
    final dominantHand = profile?.dominantHand;

    try {
      final Map<String, Test> val = await _apiCallsService.getHandsValues();
      double rightHandAverage = double.parse(val["Right"]!.trial1) +
          double.parse(val["Right"]!.trial2) +
          double.parse(val["Right"]!.trial3);
      rightHandAverage = rightHandAverage / 3;
      double leftHandAverage = double.parse(val["Left"]!.trial1) +
          double.parse(val["Left"]!.trial2) +
          double.parse(val["Left"]!.trial3);
      leftHandAverage = leftHandAverage / 3;

      if (dominantHand == "Right") {
        rightHandValue = "100 %";
        leftHandValue =
            "${(leftHandAverage / rightHandAverage * 100).toStringAsFixed(2)} %";
      } else {
        leftHandValue = "100 %";
        rightHandValue =
            "${(rightHandAverage / leftHandAverage * 100).toStringAsFixed(2)} %";
      }
    } catch (e) {
      leftHandValue = "";
      rightHandValue = "";
      takeTestToGetHandAnalysis = true;
      rebuildUi();
      _logger.e("Error in fetching hands values $e");
    }

    notifyListeners();
  }

  Future<void> sendNotification() async {
    final NotificationsService notificationsService =
        locator<NotificationsService>();
    final permission = await notificationsService.checkNotificationPermission();

    if (!permission) await notificationsService.requestNotificationPermission();

    await notificationsService.sendNotificationInSomeTime();
  }

  Future<List<Accounts>> getSpecialists() async {
    final accounts = await _apiCallsService.getSpecialists();
    return accounts;
  }
}
