import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/Model/Device.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/api_calls_service.dart';

class CreateTestDialogModel extends BaseViewModel {
  String? hand;
  late Future<List<Device>?> devicesFuture;
  String? dropDownValue;
  String? deviceId;

  final _apiCallService = locator<ApiCallsService>();
  final _accountsService = locator<AccountsService>();
  Future<List<Device>?> init() async {
    return await _accountsService.getDevices();
  }

  Future<bool> createTest(
      Assessment assessment, String hand, String deviceId) async {
    setBusy(true);
    try {
      await _apiCallService.createTestQueue(
        assessment: assessment,
        hand: hand,
        deviceId: deviceId,
      );
      Fluttertoast.showToast(msg: "Test created successfully");
      setBusy(false);
      return true;
    } catch (e) {
      Fluttertoast.showToast(msg: "Error creating test queue $e");
      setBusy(false);
      return false;
    }
  }
}
