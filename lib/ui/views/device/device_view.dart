import 'package:flutter/material.dart';
import 'package:get_storage/get_storage.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked/stacked_annotations.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Device.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/notifications_service.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/views/device/device_view.form.dart';

import 'device_viewmodel.dart';

@FormView(
  fields: [
    FormTextField(name: 'deviceName'),
    FormTextField(name: 'deviceCode'),
  ],
)
class DeviceView extends StackedView<DeviceViewModel> with $DeviceView {
  DeviceView({Key? key, required this.showExistingDevices}) : super(key: key);
  final bool showExistingDevices;

  @override
  Widget builder(
    BuildContext context,
    DeviceViewModel viewModel,
    Widget? child,
  ) {
    final inputStyle = InputDecoration(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10.0), // Add border radius
          borderSide: BorderSide.none, // Remove the default border
        ),
        fillColor: Colors.grey[200],
        filled: true);

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('Vital Step'),
        centerTitle: true,
      ),
      body: Container(
        padding: const EdgeInsets.only(left: 50.0, right: 50.0),
        child: ListView(
          children: [
            verticalSpaceMedium,
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                verticalSpaceMedium,
                const Text(
                  "Existing Devices",
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: kcMediumGrey,
                  ),
                ),
                verticalSpaceSmall,
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
                      return SizedBox(
                        height: 200,
                        child: ListView.builder(
                            itemCount: devices.length,
                            itemBuilder:
                                (BuildContext buildContext, int index) {
                              return ListTile(
                                leading: Text((index + 1).toString()),
                                title: Text(devices[index].deviceName),
                                subtitle: Text(devices[index].deviceCode),
                              );
                            }),
                      );
                    }
                  },
                ),
                verticalSpaceSmall,
              ],
            ),
            verticalSpaceMedium,
            Row(
              children: [
                const Text(
                  'Add Device',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: kcMediumGrey,
                  ),
                ),
                Spacer(),
                TextButton(
                    onPressed: () {
                      showDialog(
                        context: context,
                        builder: (BuildContext context) {
                          return Dialog(
                            child: Image.asset(
                              "assets/pair.png",
                              width: 150,
                              height: 150,
                            ),
                          );
                        },
                      );
                    },
                    child: Text("Help"))
              ],
            ),
            verticalSpaceMedium,
            TextFormField(
              controller: deviceCodeController,
              decoration: inputStyle.copyWith(
                labelText: 'Device Code',
              ),
            ),
            verticalSpaceSmall,
            SizedBox(
              width: screenWidth(context) * 0.5,
              child: TextFormField(
                controller: deviceNameController,
                decoration: inputStyle.copyWith(
                  labelText: 'Device Name',
                ),
              ),
            ),
            verticalSpaceSmall,
            ElevatedButton(
              onPressed: () async {
                if (viewModel.isBusy) return;
                await viewModel.saveDevice();
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.grey.shade200,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10.0),
                ),
              ),
              child: viewModel.isBusy
                  ? const Padding(
                      padding: EdgeInsets.all(4.0),
                      child: CircularProgressIndicator(),
                    )
                  : const Text(
                      'Save Device',
                      style: TextStyle(color: Colors.black),
                    ),
            ),
            verticalSpaceLarge,
            ElevatedButton(
              onPressed: () async {
                final box = GetStorage();
                await box.erase();
                final NotificationsService notificationsService =
                    locator<NotificationsService>();
                await notificationsService.clearAllFutureNotifications();
                NavigationService().navigateToStartupView();
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.grey.shade200,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10.0),
                ),
              ),
              child: const Text(
                'Submit',
                style: TextStyle(color: Colors.black),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  DeviceViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      DeviceViewModel();

  @override
  void onViewModelReady(DeviceViewModel viewModel) {
    syncFormWithViewModel(viewModel);
    viewModel.devicesFuture = viewModel.init();
  }
}
