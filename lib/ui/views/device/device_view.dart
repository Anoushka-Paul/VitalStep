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
    return Scaffold(
      backgroundColor: kcBackgroundColor,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text(
          'Device Pairing',
          style: TextStyle(color: kcDarkGreyColor, fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        elevation: 0,
        iconTheme: const IconThemeData(color: kcDarkGreyColor),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(25.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionTitle("Connected Devices"),
            verticalSpaceSmall,
            FutureBuilder<List<Device>?>(
              future: viewModel.devicesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError ||
                    !snapshot.hasData ||
                    snapshot.data!.isEmpty) {
                  return _buildEmptyState();
                } else {
                  final devices = snapshot.data!;
                  return ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: devices.length,
                    separatorBuilder: (c, i) => verticalSpaceSmall,
                    itemBuilder: (context, index) => _buildDeviceCard(devices[index], index),
                  );
                }
              },
            ),
            verticalSpaceMedium,
            const Divider(),
            verticalSpaceMedium,
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSectionTitle("Add New Device"),
                TextButton.icon(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (BuildContext context) {
                        return Dialog(
                          child: Padding(
                            padding: const EdgeInsets.all(20.0),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Text("Pairing Instructions", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                                verticalSpaceMedium,
                                Image.asset(
                                  "assets/pair.png",
                                  width: 150,
                                  height: 150,
                                ),
                                verticalSpaceMedium,
                                const Text("Enter the code displayed on your device screen."),
                              ],
                            ),
                          ),
                        );
                      },
                    );
                  },
                  icon: const Icon(Icons.help_outline, color: kcPrimaryColor),
                  label: const Text("Help", style: TextStyle(color: kcPrimaryColor)),
                )
              ],
            ),
            verticalSpaceSmall,
            _buildInputCard(
              controller: deviceCodeController,
              label: 'Device Code',
              hint: 'Enter 6-digit code',
              icon: Icons.qr_code,
            ),
            verticalSpaceSmall,
            _buildInputCard(
              controller: deviceNameController,
              label: 'Device Name',
              hint: 'e.g. My Left Hand Sensor',
              icon: Icons.edit,
            ),
            verticalSpaceMedium,
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: () async {
                  if (viewModel.isBusy) return;
                  await viewModel.saveDevice();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: kcPrimaryColor,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15.0),
                  ),
                  elevation: 5,
                ),
                child: viewModel.isBusy
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text(
                        'Pair Device',
                        style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
            verticalSpaceLarge,
            Center(
              child: TextButton(
                onPressed: () {
                  NavigationService().navigateToStartupView();
                },
                child: const Text(
                  'Skip to Dashboard',
                  style: TextStyle(color: kcMediumGrey, fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: kcDarkGreyColor,
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.devices_other, color: kcMediumGrey),
          horizontalSpaceSmall,
          Text("No devices paired yet", style: TextStyle(color: kcMediumGrey)),
        ],
      ),
    );
  }

  Widget _buildDeviceCard(Device device, int index) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.shade100,
            blurRadius: 5,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: kcPrimaryColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              (index + 1).toString(),
              style: const TextStyle(color: kcPrimaryColor, fontWeight: FontWeight.bold),
            ),
          ),
          horizontalSpaceMedium,
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                device.deviceName,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              Text(
                "Code: ${device.deviceCode}",
                style: const TextStyle(color: kcMediumGrey, fontSize: 14),
              ),
            ],
          ),
          const Spacer(),
          const Icon(Icons.check_circle, color: kcSuccessColor),
        ],
      ),
    );
  }

  Widget _buildInputCard({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.shade100,
            blurRadius: 5,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: TextFormField(
        controller: controller,
        decoration: InputDecoration(
          icon: Icon(icon, color: kcMediumGrey),
          labelText: label,
          hintText: hint,
          border: InputBorder.none,
          labelStyle: const TextStyle(color: kcMediumGrey),
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
