import 'dart:async';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
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
import 'package:vital_step/services/analysis_service.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:vital_step/ui/views/account/account_view.dart';
import 'package:vital_step/ui/views/assesment/assesment_view.dart';
import 'package:vital_step/ui/views/home_tab/home_tab_view.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:get_storage/get_storage.dart';


import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/ui/common/app_colors.dart';

class HomeTabViewModel extends BaseViewModel {
  final _apiCallsService = locator<ApiCallsService>();
  final _logger = getLogger("HomeTabViewModel");
  final _accountService = locator<AccountsService>();
  final _navigationService = locator<NavigationService>();
  
  Profile? profile;
  String rightHandValue = "";
  String leftHandValue = "";
  bool takeTestToGetHandAnalysis = false;
  List<Test> userTests = [];
  int streak = 0;
  String nudgeMessage = "";
  final _analysisService = locator<AnalysisService>();

  String get leftHandStrength {
    if (userTests.isEmpty) return "0.0";
    final leftTests = userTests.where((t) => t.hand == "Left").toList();
    if (leftTests.isEmpty) return "0.0";
    final last = leftTests.last;
    try {
      return ((double.parse(last.trial1) + double.parse(last.trial2) + double.parse(last.trial3)) / 3).toStringAsFixed(1);
    } catch (_) {
      return "0.0";
    }
  }

  String get rightHandStrength {
    if (userTests.isEmpty) return "0.0";
    final rightTests = userTests.where((t) => t.hand == "Right").toList();
    if (rightTests.isEmpty) return "0.0";
    final last = rightTests.last;
    try {
      return ((double.parse(last.trial1) + double.parse(last.trial2) + double.parse(last.trial3)) / 3).toStringAsFixed(1);
    } catch (_) {
      return "0.0";
    }
  }

  String get healthInsight {
    if (userTests.isEmpty) return "Welcome to Vital-step! Take your first assessment to begin tracking your hand health and receive personalized insights.";
    
    double left = double.tryParse(leftHandStrength) ?? 0;
    double right = double.tryParse(rightHandStrength) ?? 0;
    
    if (left == 0 || right == 0) return "You've started your journey! Complete assessments for both hands to get a comprehensive symmetry analysis.";
    
    double symmetry = (left > right) ? (right / left) : (left / right);
    
    if (symmetry > 0.9) return "Excellent symmetry! Your hand strength is well-balanced. Keep up with your regular exercise routine.";
    if (symmetry > 0.8) return "Good balance maintained. There is a slight variance, which is often normal, but worth monitoring over time.";
    return "Significant asymmetry detected. Consider focusing on your non-dominant hand exercises or consult your specialist for a detailed review.";
  }

  Color get healthStatusColor {
    if (userTests.isEmpty) return kcInfoColor;
    double left = double.tryParse(leftHandStrength) ?? 0;
    double right = double.tryParse(rightHandStrength) ?? 0;
    if (left == 0 || right == 0) return kcWarningColor;
    
    double symmetry = (left > right) ? (right / left) : (left / right);
    if (symmetry > 0.9) return kcSuccessColor;
    if (symmetry > 0.8) return kcWarningColor;
    return kcErrorColor;
  }


  Timer? _pollingTimer;

  Future<void> init() async {
    setBusy(true);
    await refreshData();
    setBusy(false);

    // Set up real-time polling every 10 seconds
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) => refreshData());
  }

  Future<void> refreshData() async {
    try {
      if (profile == null) {
        await getProfile();
      }
      if (profile != null) {
        await getHandsValues();
        userTests = await _apiCallsService.getAllUserTests();
        streak = _analysisService.calculateStreak(userTests);
        nudgeMessage = _analysisService.getNudgeMessage(userTests);
        notifyListeners();
      }
    } catch (e) {
      _logger.e(e);
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> getProfile() async {
    profile = await _accountService.getAccountDetails();
  }

  Future<void> getHandsValues() async {
    final dominantHand = profile?.dominantHand;

    try {
      final Map<String, Test?> val = await _apiCallsService.getHandsValues();
      
      double? rightHandAverage;
      if (val["Right"] != null) {
        rightHandAverage = (double.parse(val["Right"]!.trial1) +
            double.parse(val["Right"]!.trial2) +
            double.parse(val["Right"]!.trial3)) / 3;
      }

      double? leftHandAverage;
      if (val["Left"] != null) {
         leftHandAverage = (double.parse(val["Left"]!.trial1) +
            double.parse(val["Left"]!.trial2) +
            double.parse(val["Left"]!.trial3)) / 3;
      }

      if (rightHandAverage != null && leftHandAverage != null) {
        if (dominantHand == "Right") {
          rightHandValue = "100 %";
          leftHandValue =
              "${(leftHandAverage / rightHandAverage * 100).toStringAsFixed(2)} %";
        } else {
          leftHandValue = "100 %";
          rightHandValue =
              "${(rightHandAverage / leftHandAverage * 100).toStringAsFixed(2)} %";
        }
      } else {
         // Handle missing data without crashing
         if (leftHandAverage != null) leftHandValue = leftHandAverage.toStringAsFixed(1);
         if (rightHandAverage != null) rightHandValue = rightHandAverage.toStringAsFixed(1);
         takeTestToGetHandAnalysis = true;
      }

    } catch (e) {
      leftHandValue = "";
      rightHandValue = "";
      takeTestToGetHandAnalysis = true;
      rebuildUi();
      _logger.e("Error in fetching hands values $e");
    }
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
  Future<void> navigateToAnalysis() async {
    if (userTests.isEmpty) {
      // No test history yet — guide them to take their first test
      Fluttertoast.showToast(
        msg: "No test data yet. Take a test first to see your analysis!",
        toastLength: Toast.LENGTH_LONG,
      );
      _navigationService.navigateTo(Routes.assesmentView);
    } else {
      // Has test history — show full AI analysis of most recent test
      _navigationService.navigateTo(Routes.testResultView);
    }
  }

  Future<void> navigateToCompare() async {
    _navigationService.navigateTo(Routes.compareView);
  }

  Future<void> startHandTest(String hand) async {
    await _navigationService.navigateTo(Routes.assesmentView);
    Fluttertoast.showToast(msg: "Select an assessment for your $hand hand");
  }

  Future<void> takeTest() async {
    final DialogService _dialogService = locator<DialogService>();
    final DialogResponse? response = await _dialogService.showConfirmationDialog(
      title: "Select Hand",
      description: "Which hand would you like to test?",
      confirmationTitle: "Right Hand",
      cancelTitle: "Left Hand",
      barrierDismissible: true,
    );

    if (response == null) return; // User dismissed without choosing

    String selectedHand = response.confirmed ? "Right" : "Left";
    
    // Store for AssesmentViewModel to pick up
    final _box = GetStorage();
    _box.write("preSelectedHand", selectedHand);

    await _navigationService.navigateTo(Routes.assesmentView);
    Fluttertoast.showToast(
      msg: "Assigned to $selectedHand hand. Please select or create an assessment.",
      toastLength: Toast.LENGTH_LONG,
    );
  }

  List<FlSpot> getGraphData(String hand) {
    if (userTests.isEmpty) return [];
    
    final handTests = userTests.where((t) => t.hand == hand).toList();
    // Limit to last 10 tests for the "10 days" requirement visual
    final recentTests = handTests.length > 10 
        ? handTests.sublist(handTests.length - 10) 
        : handTests;

    List<FlSpot> spots = [];
    for (int i = 0; i < recentTests.length; i++) {
        double avg = (double.parse(recentTests[i].trial1) + 
                      double.parse(recentTests[i].trial2) + 
                      double.parse(recentTests[i].trial3)) / 3;
        spots.add(FlSpot(i.toDouble(), avg));
    }
    return spots;
  }

  Future<void> contactSpecialistViaWhatsApp(String? phone, String? countryCode) async {
    if (phone == null || phone.isEmpty) {
      Fluttertoast.showToast(msg: "No specialist number available");
      return;
    }
    
    final cleanPhone = phone.replaceAll(RegExp(r'\D'), '');
    final cleanCode = (countryCode ?? "+91").replaceAll(RegExp(r'\D'), '');
    final url = "whatsapp://send?phone=$cleanCode$cleanPhone&text=Hello, I am using the VitalStep app and would like to discuss my assessments.";
    
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url));
    } else {
      // Fallback to web link if app isn't installed
      final webUrl = "https://wa.me/$cleanCode$cleanPhone";
      await launchUrl(Uri.parse(webUrl), mode: LaunchMode.externalApplication);
    }
  }

  Future<void> contactSpecialistViaCall(String? phone) async {
    if (phone == null || phone.isEmpty) {
      Fluttertoast.showToast(msg: "No specialist number available");
      return;
    }
    final url = "tel:${phone.replaceAll(RegExp(r'\D'), '')}";
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url));
    } else {
      Fluttertoast.showToast(msg: "Could not launch dialer");
    }
  }
}
