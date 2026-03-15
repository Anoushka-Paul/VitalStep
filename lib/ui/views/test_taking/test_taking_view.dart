import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'test_taking_viewmodel.dart';

class TestTakingView extends StackedView<TestTakingViewModel> {
  const TestTakingView({Key? key, required this.assessment}) : super(key: key);
  final Assessment assessment;
  @override
  Widget builder(
    BuildContext context,
    TestTakingViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close_rounded, color: kcDarkGreyColor),
          onPressed: () => viewModel.cancelTest(assessment: assessment),
        ),
        title: const Text(
          "Grip Test",
          style: TextStyle(color: kcDarkGreyColor, fontWeight: FontWeight.bold, fontSize: 18, letterSpacing: -0.5),
        ),
        centerTitle: true,
      ),
      body: Container(
        padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 40),
        child: Column(
          children: [
            const Spacer(),
            Container(
              padding: const EdgeInsets.all(40),
              decoration: BoxDecoration(
                color: kcPrimaryColor.withOpacity(0.05),
                shape: BoxShape.circle,
              ),
              child: Image.asset(
                "assets/test.png",
                height: 180,
                width: 180,
                fit: BoxFit.contain,
              ),
            ),
            verticalSpaceLarge,
            const Text(
              "Ready to Start?",
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: kcDarkGreyColor),
            ),
            verticalSpaceSmall,
            const Text(
              "Follow the on-screen instructions. Squeeze the dynamometer as hard as you can when prompted.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16, color: kcMediumGrey, height: 1.5),
            ),
            const Spacer(),
            _buildGuidanceCard(),
            verticalSpaceLarge,
            _buildStartButton(viewModel),
          ],
        ),
      ),
    );
  }

  Widget _buildGuidanceCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kcSecondaryColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kcSecondaryColor.withOpacity(0.1)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: kcSecondaryColor),
          horizontalSpaceSmall,
          const Expanded(
            child: Text(
              "Ensure you are sitting upright with your arm at a 90° angle.",
              style: TextStyle(fontSize: 13, color: kcSecondaryColor, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStartButton(TestTakingViewModel vm) {
    return InkWell(
      onTap: () => vm.takeTest(assessment),
      borderRadius: BorderRadius.circular(24),
      child: Container(
        width: double.infinity,
        height: 64,
        decoration: BoxDecoration(
          gradient: kcPrimaryGradient,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: kcPrimaryColor.withOpacity(0.35),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Center(
          child: vm.isBusy
              ? const CircularProgressIndicator(color: Colors.white)
              : const Text(
                  "Begin Assessment",
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
                ),
        ),
      ),
    );
  }

  @override
  TestTakingViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      TestTakingViewModel();
}
