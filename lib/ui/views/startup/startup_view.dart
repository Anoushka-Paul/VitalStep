import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'startup_viewmodel.dart';

class StartupView extends StackedView<StartupViewModel> {
  const StartupView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    StartupViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Image.asset(
            'assets/Logo.jpeg',
            width: 150,
            height: 150,
          ),
          verticalSpaceSmall,
          const Center(
            child: Text(
              'Vital Step',
              style: TextStyle(
                // letterSpacing: 5,
                fontSize: 30,
              ),
            ),
          ),
          verticalSpaceMedium,
          Center(
            child: const CircularProgressIndicator(
              color: kcPrimaryColor,
            ),
          ),
        ],
      ),
    );
  }

  @override
  StartupViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      StartupViewModel();

  @override
  void onViewModelReady(StartupViewModel viewModel) => SchedulerBinding.instance
      .addPostFrameCallback((timeStamp) => viewModel.runStartupLogic());
}
