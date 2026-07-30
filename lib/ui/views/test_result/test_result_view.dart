import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/mode_service.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vital_step/ui/widgets/common/analysis_radar_chart.dart';
import 'test_result_viewmodel.dart';

class TestResultView extends StackedView<TestResultViewModel> {
  const TestResultView({Key? key}) : super(key: key);

  @override
  void onViewModelReady(TestResultViewModel viewModel) {
    viewModel.initialise();
  }

  @override
  Widget builder(
    BuildContext context,
    TestResultViewModel viewModel,
    Widget? child,
  ) {
    void handleBack() {
      final modeService = locator<ModeService>();
      if (modeService.isPatientMode && modeService.hasActivePatient) {
        // Clear the stack back to patient session so the user can't
        // accidentally pop back into the test taking waiting screen.
        NavigationService().clearStackAndShow(Routes.patientSessionView);
      } else {
        NavigationService().clearStackAndShow(
          Routes.homeView,
          arguments: const HomeViewArguments(firstPage: 1),
        );
      }
    }

    return PopScope(
      // Intercept the Android system back button so it mirrors the AppBar back button
      // instead of letting Flutter pop (or close the app if the stack is empty).
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) handleBack();
      },
      child: Scaffold(
        backgroundColor: kcBackgroundColor,
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          title: const Text(
            "Test Result",
            style: TextStyle(
                color: kcDarkGreyColor,
                fontWeight: FontWeight.bold,
                fontSize: 20),
          ),
          centerTitle: true,
          leading: IconButton(
            onPressed: handleBack,
            icon: const Icon(Icons.arrow_back_ios_new,
                color: kcDarkGreyColor, size: 20),
          ),
          actions: [
            IconButton(
              onPressed: () {
                viewModel.initialise();
                viewModel.notifyListeners();
              },
              icon: const Icon(Icons.refresh, color: kcPrimaryColor),
            ),
          ],
        ),
        body: FutureBuilder(
          future: viewModel.testFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                  child: CircularProgressIndicator(color: kcPrimaryColor));
            }
            final test = snapshot.data;
            if (test == null)
              return const Center(
                  child: Text("Results not found",
                      style: TextStyle(color: kcMediumGrey)));

            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildPremiumHeader(viewModel, test),
                  verticalSpaceMedium,
                  FutureBuilder(
                    future: viewModel.getAiInsight(),
                    builder: (context, insightSnapshot) {
                      if (insightSnapshot.connectionState == ConnectionState.waiting) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.all(20),
                            child: CircularProgressIndicator(color: kcPrimaryColor),
                          ),
                        );
                      }
                      return _buildMetricSection(
                        "AI Performance Insight",
                        _buildAiInsightCard(insightSnapshot.data ?? "Loading...")
                      );
                    },
                  ),
                  verticalSpaceMedium,
                  _buildMetricSection(
                      "Detailed Analysis", _buildRadarChartCard(viewModel)),
                  verticalSpaceMedium,
                  _buildMetricSection("Trial Details", _buildTrialsCard(test)),
                  verticalSpaceMedium,
                  FutureBuilder(
                    future: viewModel.getRecoveryTips(),
                    builder: (context, tipsSnapshot) {
                      if (tipsSnapshot.connectionState == ConnectionState.waiting) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.all(20),
                            child: CircularProgressIndicator(color: kcPrimaryColor),
                          ),
                        );
                      }
                      return _buildRecoverySection(tipsSnapshot.data ?? []);
                    },
                  ),
                  verticalSpaceLarge,
                  _buildActionButtons(viewModel),
                  verticalSpaceLarge,
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildMetricSection(String title, Widget content) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: kcDarkGreyColor)),
        verticalSpaceSmall,
        content,
      ],
    );
  }

  Widget _buildPremiumHeader(TestResultViewModel vm, dynamic test) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
            colors: [kcPrimaryColor, kcPrimaryColorDark],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
              color: kcPrimaryColor.withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 10))
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(vm.getDate(test.createdAt),
                  style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      fontWeight: FontWeight.w600)),
              verticalSpaceTiny,
              const Text("Latest Assessment",
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold)),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white30)),
            child: Text(test.hand.toUpperCase(),
                style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 14)),
          )
        ],
      ),
    );
  }

  Widget _buildAiInsightCard(String insight) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: premiumCardDecoration.copyWith(
          color: kcPrimaryColor.withOpacity(0.03),
          border: Border.all(color: kcPrimaryColor.withOpacity(0.1))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.auto_awesome, color: kcPrimaryColor, size: 24),
          horizontalSpaceSmall,
          Expanded(
            child: Text(
              insight,
              style: const TextStyle(
                  fontSize: 15,
                  color: kcDarkGreyColor,
                  height: 1.5,
                  fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadarChartCard(TestResultViewModel vm) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: premiumCardDecoration,
      child: Center(
        child: AnalysisRadarChart(
          peakStrength: vm.peakMetric,
          consistency: vm.consistencyMetric,
          symmetry: vm.symmetryMetric,
        ),
      ),
    );
  }

  Widget _buildTrialsCard(dynamic test) {
    // Format trial values to 2 decimal places
    String fmt(dynamic val) {
      final d = double.tryParse(val?.toString() ?? '');
      return d != null ? d.toStringAsFixed(2) : (val?.toString() ?? '-');
    }

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: premiumCardDecoration,
      child: Column(
        children: [
          _buildResultRow("Posture", test.posture, isPrimary: true),
          const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Divider(height: 1, color: kcLightGrey)),
          _buildResultRow("Reading 1", "${fmt(test.trial1)} Kg"),
          verticalSpaceSmall,
          _buildResultRow("Reading 2", "${fmt(test.trial2)} Kg"),
          verticalSpaceSmall,
          _buildResultRow("Reading 3", "${fmt(test.trial3)} Kg"),
        ],
      ),
    );
  }

  Widget _buildResultRow(String label, String val, {bool isPrimary = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: TextStyle(
                color: kcMediumGrey,
                fontSize: 14,
                fontWeight: isPrimary ? FontWeight.w600 : FontWeight.normal)),
        Text(val,
            style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: kcDarkGreyColor,
                fontSize: 15)),
      ],
    );
  }

  Widget _buildRecoverySection(List<String> tips) {
    if (tips.isEmpty) return const SizedBox();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("AI Recommended Guidance",
            style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: kcDarkGreyColor)),
        verticalSpaceSmall,
        ...tips.map((tip) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.green.withOpacity(0.1))),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline,
                      color: Colors.green, size: 20),
                  horizontalSpaceSmall,
                  Expanded(
                      child: Text(tip,
                          style: const TextStyle(
                              fontSize: 14,
                              color: kcDarkGreyColor,
                              fontWeight: FontWeight.w500))),
                ],
              ),
            )),
      ],
    );
  }

  Widget _buildActionButtons(TestResultViewModel vm) {
    return Column(
      children: [
        ElevatedButton(
          onPressed: vm.shareDetailedReport,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xff25D366),
            minimumSize: const Size(double.infinity, 60),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            elevation: 0,
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.share, color: Colors.white, size: 20),
              horizontalSpaceSmall,
              Text("Share Detailed Report",
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16)),
            ],
          ),
        ),
        verticalSpaceSmall,
        TextButton(
          onPressed: () async {
            final url = Uri.parse(
                "https://www.google.com/search?q=hand+specialist+near+me");
            if (await canLaunchUrl(url))
              await launchUrl(url, mode: LaunchMode.externalApplication);
          },
          child: const Text("Find a Hand Specialist Near Me",
              style: TextStyle(
                  color: kcPrimaryColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  decoration: TextDecoration.underline)),
        ),
      ],
    );
  }

  @override
  viewModelBuilder(BuildContext context) => TestResultViewModel();
}
