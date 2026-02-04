import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/Assessment.dart';

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
      appBar: AppBar(
        automaticallyImplyLeading: false,
        backgroundColor: Colors.white,
        title: const Text("Take Test "),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            viewModel.cancelTest(assessment: assessment);
          },
        ),
        actions: [],
      ),
      backgroundColor: Colors.white,
      body: Container(
        padding: const EdgeInsets.only(left: 25.0, right: 25.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            Image.asset(
              "assets/test.png",
              height: 200,
              width: 200,
            ),
            const Text(
              "Click on the test button to start the test, Once completed then tap the results button",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            Container(
              padding: const EdgeInsets.only(top: 20.0),
              child: ElevatedButton(
                onPressed: () {
                  viewModel.takeTest(assessment);
                },
                child: viewModel.isBusy
                    ? const CircularProgressIndicator()
                    : const Text("See Test Results"),
              ),
            ),
          ],
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
