import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Device.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.logger.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/ui/views/device/device_view.form.dart';

class DeviceViewModel extends FormViewModel {
  final _dialogService = locator<DialogService>();
  final _accountsService = locator<AccountsService>();
  final _apiCallsService = locator<ApiCallsService>();
  final _logger = getLogger("DeviceViewModel");
  late Future<List<Device>?> devicesFuture;
  List<Device>? devices;
  List<String>? deviceCodes;
  Future<List<Device>?> init() async {
    devices = await _accountsService.getDevices();
    await getAllPossibleDevices();
    return devices;
  }

  Future<void> saveDevice() async {
    setBusy(true);
    if (deviceCodeValue == null || deviceCodeValue!.isEmpty) {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: "Device Code Error",
          description: "The device code can not be empty. Please try again.");
    } else if (deviceNameValue == null || deviceNameValue!.isEmpty) {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: "Device Name Error",
          description: "The device Name can not be empty. Please try again.");
    } else if (deviceCodes == null) {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: "Device Code Error",
          description: "Unable to fetch device codes. Please try again.");
    } else if (deviceCodes!.isEmpty) {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: "Device Code Error",
          description: "No device codes available. Please try again.");
    } else if (!deviceCodes!.contains(deviceCodeValue)) {
      _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: "Device Code Error",
          description:
              "The device code is not valid. Please enter a valid device code.");
    } else {
      try {
        await _accountsService.addDevice(
            deviceCode: deviceCodeValue!, deviceName: deviceNameValue!);
        Fluttertoast.showToast(msg: "Device added successfully");

        devicesFuture = init();
      } catch (e) {
        _logger.e(e.toString());
        Fluttertoast.showToast(msg: "Unable to add device");
      }
    }
    setBusy(false);
  }

  Future<void> getAllPossibleDevices() async {
    try {
      deviceCodes = await _apiCallsService.getAllPossibleDevices();
      _logger.i(deviceCodes);
    } catch (e) {
      _logger.e(e.toString());
      Fluttertoast.showToast(msg: "Unable to fetch devices");
    }
  }
}
