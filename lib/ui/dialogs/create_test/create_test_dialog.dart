import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/Model/Device.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';

import 'create_test_dialog_model.dart';

const double _graphicSize = 60;

class CreateTestDialog extends StackedView<CreateTestDialogModel> {
  final DialogRequest request;
  final Function(DialogResponse) completer;

  const CreateTestDialog({
    Key? key,
    required this.request,
    required this.completer,
  }) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    CreateTestDialogModel viewModel,
    Widget? child,
  ) {
    final Assessment assessment = Assessment.fromJson(request.data);
    print(assessment);
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      backgroundColor: Colors.white,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Create Test',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Text(
              'Select hand',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey,
              ),
            ),
            Row(
              children: [
                Checkbox(
                    value: viewModel.hand == "Right" ? true : false,
                    onChanged: (val) {
                      viewModel.hand = "Right";
                      viewModel.rebuildUi();
                    }),
                horizontalSpaceSmall,
                const Text("Right"),
              ],
            ),
            Row(
              children: [
                Checkbox(
                    value: viewModel.hand == "Left" ? true : false,
                    onChanged: (val) {
                      viewModel.hand = "Left";
                      viewModel.rebuildUi();
                    }),
                horizontalSpaceSmall,
                const Text("Left"),
              ],
            ),
            const Text(
              'Select the device',
              style: const TextStyle(
                fontSize: 16,
                color: Colors.grey,
              ),
            ),
            FutureBuilder<List<Device>?>(
              future: viewModel.devicesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const SizedBox(
                    height: 200,
                    child: Center(
                      child: CircularProgressIndicator(),
                    ),
                  );
                } else if (snapshot.hasError) {
                  return const Text("Error fetching devices");
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return const Text("No devices found");
                } else {
                  final devices = snapshot.data!;
                  final List<String> deviceNames =
                      devices.map((device) => device.deviceName).toList();
                  return SizedBox(
                    width: double.infinity,
                    child: DropdownButton<String>(
                      isExpanded: true,
                      value: viewModel.dropDownValue,
                      icon: const Icon(Icons.arrow_downward),
                      iconSize: 24,
                      elevation: 16,
                      onChanged: (String? newValue) {
                        viewModel.dropDownValue = newValue!;
                        viewModel.deviceId = devices
                            .firstWhere(
                                (device) => device.deviceName == newValue)
                            .id
                            .toString();
                        viewModel.rebuildUi();
                      },
                      items: deviceNames
                          .map<DropdownMenuItem<String>>((String value) {
                        return DropdownMenuItem<String>(
                          value: value,
                          child: Text(value),
                        );
                      }).toList(),
                    ),
                  );
                }
              },
            ),
            GestureDetector(
              onTap: () async {
                // Simple validation
                if (viewModel.hand == null || viewModel.deviceId == null) {
                  Fluttertoast.showToast(msg: "Please select hand and device");
                } else {
                  final testResponse = await viewModel.createTest(
                      assessment, viewModel.hand!, viewModel.deviceId!);
                  if (testResponse) {
                    completer(DialogResponse(confirmed: true));
                    NavigationService()
                        .navigateToTestTakingView(assessment: assessment);
                  }
                }
              },
              child: Container(
                height: 50,
                width: double.infinity,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Colors.black,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: viewModel.isBusy
                    ? const CircularProgressIndicator()
                    : const Text(
                        'Start Test',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  CreateTestDialogModel viewModelBuilder(BuildContext context) =>
      CreateTestDialogModel();
  @override
  void onViewModelReady(CreateTestDialogModel viewModel) async {
    viewModel.devicesFuture = viewModel.init();
  }
}
