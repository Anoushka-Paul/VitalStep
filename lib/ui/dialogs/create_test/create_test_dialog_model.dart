import 'package:flutter/material.dart';
import 'package:get_storage/get_storage.dart';
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
  final patientNameController = TextEditingController();
  final ageController = TextEditingController();
  final purposeController = TextEditingController();
  final _box = GetStorage();

  Future<List<Device>?> init({String? preSelectedHand}) async {
    if (preSelectedHand != null) {
      hand = preSelectedHand;
    } else {
      hand = "Right"; // Default to Right
    }
    
    // Pre-fill last used details to speed up testing
    patientNameController.text = _box.read('last_patient_name') ?? "";
    ageController.text = _box.read('last_patient_age') ?? "";
    purposeController.text = _box.read('last_purpose') ?? "Routine Assessment";

    final devices = await _accountsService.getDevices();
    if (devices.isNotEmpty) {
      dropDownValue = devices.first.deviceName;
      deviceId = devices.first.id.toString();
    }
    rebuildUi();
    return devices;
  }

  void savePatientDetails() {
    _box.write('last_patient_name', patientNameController.text);
    _box.write('last_patient_age', ageController.text);
    _box.write('last_purpose', purposeController.text);
    // You could also store a list of these if needed for history
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

  @override
  void dispose() {
    patientNameController.dispose();
    ageController.dispose();
    purposeController.dispose();
    super.dispose();
  }
}
