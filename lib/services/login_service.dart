import 'dart:convert';

import 'package:fluttertoast/fluttertoast.dart';
import 'package:get_storage/get_storage.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/SignUpInfo.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.logger.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/notifications_service.dart';
import 'package:vital_step/ui/common/app_strings.dart';
import 'package:http/http.dart' as http;

class LoginService {
  final _logger = getLogger("LoginService");
  final box = GetStorage();
  final DialogService _dialogService = locator<DialogService>();

  /// this function will check if the user is currently logged in or not
  Future<bool> isLoggedIn() async {
    try {
      final userId = await getUserId();
      return userId != null;
    } catch (e) {
      _logger.e('Failed to check if user is logged in, error: $e');
      return false;
    }
  }

  Future<String> getUserId() async {
    try {
      final userId = box.read("userId");
      return userId;
    } catch (e) {
      _logger.e('Failed to get userId, error: $e');
      rethrow;
    }
  }

  Future<void> signIn(
      String email, String password, String selectedUserType) async {
    // selectedUserType = "Patient", "Specialist";
    final requestUrl = selectedUserType == 'Patient'
        ? '$apiBaseUrl/auth/login'
        : '$apiBaseUrl/auth/login-specialist';
    var headers = {
      'Content-Type': 'application/json',
    };
    var request = http.Request('POST', Uri.parse(requestUrl));
    request.body = json.encode({"email": email, "password": password});
    request.headers.addAll(headers);

    http.StreamedResponse streamedResponse = await request.send();
    http.Response response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      final cookie = response.headers['set-cookie'];
      final json = jsonDecode(response.body);
      final userId = json['id'].toString();
      box.write("cookie", cookie);
      box.write('userId', userId);
      box.write('userType', selectedUserType);
      NavigationService().navigateToStartupView();
    } else if (response.statusCode == 404) {
      _logger.e('Failed to login, status code: ${response.statusCode}');
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Logging In',
        description: 'The account does not exists',
      );
    } else if (response.statusCode == 400) {
      _logger.e('Failed to login, status code: ${response.statusCode}');
      var description = 'The password is wrong';

      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Logging In',
        description: description,
      );
    } else if (response.statusCode == 401 && selectedUserType == 'Specialist') {
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Logging In',
        description:
            "Your Account is still under review, please try again in some time. ",
      );
    } else {
      _logger.e('Failed to login, status code: ${response.statusCode}');
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Logging In',
        description: 'An error occurred',
      );
    }
  }

  Future<void> signUp(SignUpInfo signUpInfo) async {
    var headers = {
      'Content-Type': 'application/json',
    };
    var request = http.Request('POST', Uri.parse('$apiBaseUrl/auth/register'));

    request.body = json.encode(signUpInfo.toJson());
    _logger.i('Request body: ${request.body}');
    request.headers.addAll(headers);

    http.StreamedResponse streamedResponse = await request.send();
    http.Response response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      String? cookie = response.headers['set-cookie'];
      final userId = json[0]['id'].toString();

      cookie ??= await getCookie(
          userId: userId,
          email: signUpInfo.email,
          password: signUpInfo.password);
      if (cookie == null) {
        _logger.e('Failed to get cookie');
        _dialogService.showCustomDialog(
          variant: DialogType.infoAlert,
          title: 'Error Signing Up',
          description: 'An error occurred',
        );
        return;
      }
      _logger.i('User registered successfully, userId: $userId');
      box.write("cookie", cookie);
      box.write('userId', userId);
      NavigationService().navigateToDeviceView(showExistingDevices: false);
    } else if (response.statusCode == 404) {
      _logger.e(
          'Failed to create a Account, status code: ${response.statusCode}, Account Already exists');
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Unable to create a new account',
        description: 'Unable to create a new account, Account Already exists',
      );
    } else {
      _logger.e('Failed to Signup, status code: ${response.statusCode}');
      _logger.e('Unable to sign Up: ${response.body}');
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Signing Up',
        description: 'An error occurred',
      );
    }
  }

  Future<void> signOut() async {
    await box.erase();
    final NotificationsService notificationsService =
        locator<NotificationsService>();
    await notificationsService.clearAllFutureNotifications();
    Fluttertoast.showToast(msg: "User Logged Out Successfully");
    NavigationService().navigateToStartupView();
  }

  Future<String?> getCookie(
      {required String userId,
      required String email,
      required String password}) async {
    var headers = {
      'Content-Type': 'application/json',
    };
    var request = http.Request('POST', Uri.parse('$apiBaseUrl/auth/login'));
    request.body = json.encode({"email": email, "password": password});
    request.headers.addAll(headers);

    http.StreamedResponse streamedResponse = await request.send();
    http.Response response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      final cookie = response.headers['set-cookie'];
      return cookie;
    } else {
      _logger.e('Failed to get cookie, status code: ${response.statusCode}');
      return null;
    }
  }

  updateProfile(SignUpInfo signUpInfo) async {
    final cookie = box.read('cookie').toString();
    var headers = {
      "accept": "application/json",
      'Content-Type': 'application/json',
      "cookie": cookie,
    };
    final userId = box.read('userId');
    final address = '$apiBaseUrl/user/$userId';
    var request = http.Request('PUT', Uri.parse(address));

    request.body = json.encode(signUpInfo.toJson());
    request.headers.addAll(headers);

    http.StreamedResponse streamedResponse = await request.send();
    http.Response response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      Fluttertoast.showToast(msg: "Profile Updated Successfully");
    } else {
      _logger
          .e('Failed to update profile, status code: ${response.statusCode}');
      _dialogService.showCustomDialog(
        variant: DialogType.infoAlert,
        title: 'Error Updating Profile',
        description: 'An error occurred',
      );
    }
  }

  Future<String> getUserType() async {
    final userType = box.read('userType');
    return userType;
  }
}
