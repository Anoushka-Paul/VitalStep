import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'test_result_viewmodel.dart';

class TestResultView extends StackedView<TestResultViewModel> {
  const TestResultView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    TestResultViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text("Test Results"),
        centerTitle: true,
        actions: [
          IconButton(
              onPressed: () {
                viewModel.testFuture = viewModel.init();
                viewModel.rebuildUi();
              },
              icon: Icon(Icons.refresh)),
        ],
      ),
      body: Container(
        padding: const EdgeInsets.only(left: 25.0, right: 25.0),
        child: FutureBuilder(
          future: viewModel.testFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(
                child: CircularProgressIndicator(),
              );
            } else {
              final test = snapshot.data;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ResultRow(
                    heading: "Test Date - ",
                    value: viewModel.getDate(test!.createdAt),
                  ),
                  ResultRow(
                    heading: "Test Time - ",
                    value: viewModel.getTime(test!.createdAt),
                  ),
                  ResultRow(
                    heading: "Posture - ",
                    value: test.posture,
                  ),
                  ResultRow(
                    heading: "Hand - ",
                    value: test.hand,
                  ),
                  ResultRow(
                    heading: "Trial 1 - ",
                    value: "${test.trial1} Kg",
                  ),
                  ResultRow(
                    heading: "Trial 2 - ",
                    value: "${test.trial2} Kg",
                  ),
                  ResultRow(
                    heading: "Trial 3 - ",
                    value: "${test.trial3} Kg",
                  ),
                ],
              );
            }
          },
        ),
      ),
    );
  }

  @override
  TestResultViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      TestResultViewModel();

  @override
  void onViewModelReady(TestResultViewModel viewModel) {
    viewModel.testFuture = viewModel.init();
  }
}

class ResultRow extends StatelessWidget {
  const ResultRow({
    super.key,
    required this.heading,
    required this.value,
  });
  final String heading, value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        verticalSpaceMedium,
        Row(
          children: [
            Text(
              heading,
              style: const TextStyle(fontSize: 20),
            ),
            horizontalSpaceSmall,
            Text(
              value,
              style: const TextStyle(fontSize: 20),
            ),
          ],
        ),
      ],
    );
  }
}
