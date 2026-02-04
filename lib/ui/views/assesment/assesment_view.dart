import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/Model/accounts.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';

import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'assesment_viewmodel.dart';

class AssesmentView extends StackedView<AssesmentViewModel> {
  const AssesmentView({
    Key? key,
    this.isSpecialist,
    this.patientAccount,
  }) : super(key: key);
  final bool? isSpecialist;
  final Accounts? patientAccount;

  @override
  Widget builder(
    BuildContext context,
    AssesmentViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text("Assessment"),
        centerTitle: true,
        automaticallyImplyLeading: isSpecialist == true ? true : false,
        actions: [
          isSpecialist == true
              ? const SizedBox()
              : IconButton(
                  onPressed: () {
                    NavigationService()
                        .navigateToDeviceView(showExistingDevices: false);
                  },
                  icon: const Icon(
                    Icons.devices,
                  ),
                ),
        ],
      ),
      body: Column(
        children: [
          Container(
            color: kcPrimaryColor.withAlpha(10),
            child: SingleChildScrollView(
              physics: BouncingScrollPhysics(),
              scrollDirection: Axis.vertical,
              child: FutureBuilder<List<Assessment>?>(
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
                    return const Text("Error fetching test");
                  } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return const Text("No test found");
                  } else if (snapshot.data == null) {
                    return const Text("No test found");
                  } else {
                    final devices = snapshot.data!;
                    return Container(
                      color: Colors.white,
                      height: screenWidth(context),
                      child: ListView.builder(
                          itemCount: devices.length,
                          itemBuilder: (BuildContext buildContext, int index) {
                            return InkWell(
                              onTap: () {
                                NavigationService()
                                    .navigateToAssessmentDetailView(
                                  patientUserId: patientAccount?.user.id!,
                                  assessment: devices[index],
                                  isSpecialist: isSpecialist,
                                );
                              },
                              child: ListTile(
                                  leading: Text((index + 1).toString()),
                                  title: Text(devices[index].type),
                                  subtitle: Text(
                                      "${devices[index].posture} | ${devices[index].status}"),
                                  trailing: isSpecialist == true
                                      ? IconButton(
                                          onPressed: () {
                                            viewModel.deleteAssessment(
                                                assessmentId: devices[index]
                                                    .id
                                                    .toString());
                                          },
                                          icon: const Icon(
                                            Icons.delete,
                                          ))
                                      : MaterialButton(
                                          disabledColor: Colors.grey,
                                          onPressed: () {
                                            if (devices[index]
                                                    .currentlyActive ==
                                                true) {
                                              viewModel
                                                  .takeTest(devices[index]);
                                            } else {
                                              Fluttertoast.showToast(
                                                  msg:
                                                      "Please complete the already running test.  ");
                                            }
                                          },
                                          color:
                                              devices[index].currentlyActive ==
                                                      true
                                                  ? kcPrimaryColor
                                                  : Colors.grey,
                                          child: const Text(
                                            "Take Test",
                                            style:
                                                TextStyle(color: Colors.white),
                                          ),
                                        )),
                            );
                          }),
                    );
                  }
                },
              ),
            ),
          ),
          const Spacer(),
          isSpecialist == true
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    SizedBox(width: screenWidth(context)),
                    SizedBox(
                      width: screenWidth(context) * 0.8,
                      child: MaterialButton(
                        color: const Color(0xff0101d3),
                        onPressed: () async {
                          if (viewModel.isBusy) return;
                          viewModel.setBusy(true);
                          try {
                            final Profile profile =
                                await viewModel.getPatientProfile(
                                    patientUserId: patientAccount?.user.id);
                            viewModel.setBusy(false);
                            showDialog(
                                context: context,
                                builder: (context) {
                                  return Dialog(
                                    child: Padding(
                                      padding: const EdgeInsets.all(16.0),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          const Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Text(
                                                'User Details',
                                                style: TextStyle(
                                                  fontSize: 20,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 16),
                                          Text('Name: ${profile.name}'),
                                          Text('Email: ${profile.email}'),
                                          Text(
                                              'Phone Number: ${profile.phone}'),
                                          // Add more fields as necessary
                                          const SizedBox(height: 16),
                                          Center(
                                            child: MaterialButton(
                                              color: kcPrimaryColor,
                                              onPressed: () {
                                                Navigator.of(context).pop();
                                              },
                                              child: const Text(
                                                'Close',
                                                style: TextStyle(
                                                    color: Colors.white),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                });
                          } catch (e) {
                            viewModel.setBusy(false);
                            Fluttertoast.showToast(
                                msg: "Unable to show the account details");
                          }
                        },
                        child: viewModel.isBusy
                            ? const CircularProgressIndicator(
                                color: Colors.white,
                              )
                            : const Text(
                                'User Details',
                                style: TextStyle(color: Colors.white),
                              ),
                      ),
                    ),
                    verticalSpaceSmall,
                    SizedBox(
                      width: screenWidth(context) * 0.8,
                      child: MaterialButton(
                        color: kcPrimaryColor,
                        onPressed: () async {
                          final DialogService dialogService =
                              locator<DialogService>();
                          await dialogService.showCustomDialog(
                              variant: DialogType.createAssessment,
                              data: patientAccount?.user.id);
                          viewModel.devicesFuture = viewModel.init();
                          viewModel.rebuildUi();
                        },
                        child: const Text(
                          'Create Assessment',
                          style: TextStyle(color: Colors.white),
                        ),
                      ),
                    ),
                    verticalSpaceSmall,
                    SizedBox(
                      width: screenWidth(context) * 0.8,
                      child: MaterialButton(
                        color: Color(0xfff44236),
                        onPressed: () {
                          if (viewModel.busy(viewModel.deletingUser)) return;
                          viewModel.deleteUser(patientAccount?.id);
                        },
                        child: viewModel.busy(viewModel.deletingUser)
                            ? const CircularProgressIndicator(
                                color: Colors.white,
                              )
                            : const Text(
                                'Delete User',
                                style: TextStyle(color: Colors.white),
                              ),
                      ),
                    )
                  ],
                )
              : const SizedBox()
        ],
      ),
    );
  }

  @override
  AssesmentViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      AssesmentViewModel();

  @override
  void onViewModelReady(AssesmentViewModel viewModel) async {
    viewModel.patientUserId = patientAccount?.user.id;
    viewModel.isSpecialist = isSpecialist;
    viewModel.devicesFuture = viewModel.init();
  }
}
