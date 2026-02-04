import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.logger.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/login_service.dart';

class AccountViewModel extends BaseViewModel {
  final _logger = getLogger("AccountViewModel");
  final DialogService _dialogService = locator<DialogService>();
  final _accountService = locator<AccountsService>();
  Profile? profile;
  void signOut() async {
    final loginService = locator<LoginService>();
    await loginService.signOut();
  }

  Future<void> init() async {
    profile = await _accountService.getAccountDetails();
    notifyListeners();
  }

  Map<String, dynamic> getDevices(Profile profile) {
    final devices = profile.device;
    if (devices == null) {
      return {'No devices': 'Click to add a device'};
    }
    final deviceMap = <String, dynamic>{};

    for (final device in devices) {
      String deviceDesc = device.deviceName;
      deviceMap[device.id.toString()] = deviceDesc;
    }
    if (deviceMap.isEmpty) {
      deviceMap['No devices'] = 'Click to add a device';
    }
    return deviceMap;
  }

  void deleteAccount() async {
    final response = await _dialogService.showConfirmationDialog(
      title: 'Delete Account',
      description: 'Are you sure you want to delete your account?',
      cancelTitle: 'Cancel',
    );
    response!.confirmed
        ? await _accountService.deleteAccount()
        : _logger.i('User cancelled');
  }
}
