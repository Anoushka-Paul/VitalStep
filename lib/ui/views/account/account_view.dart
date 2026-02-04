import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/NavOption.dart' as clickable_nav_option;
import 'package:vital_step/ui/common/ScreenHeading.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/widgets/common/nav_option/nav_option.dart';

import 'account_viewmodel.dart';

class AccountView extends StackedView<AccountViewModel> {
  const AccountView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    AccountViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Container(
        padding: const EdgeInsets.all(25),
        color: Colors.white,
        child: ListView(
          children: [
            ScreenHeading(heading: "Account", showBackButton: false),
            Container(
              padding: const EdgeInsets.only(bottom: 10, top: 30),
              child: Row(
                children: [
                  const Text(
                    "PROFILE",
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color.fromARGB(255, 156, 149, 149)),
                  ),
                  const Spacer(),
                  InkWell(
                    onTap: () {
                      if (viewModel.profile != null) {
                        NavigationService()
                            .navigateToSignUpView(profile: viewModel.profile);
                      }
                    },
                    child: Text(
                      "Edit Profile!",
                      style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey.shade700),
                    ),
                  ),
                ],
              ),
            ),
            viewModel.profile == null
                ? const Center(child: CircularProgressIndicator())
                : Container(
                    color: Colors.white,
                    child: Column(
                      children: [
                        NavOption("Profile", Icons.person_outline,
                            data: viewModel.profile!.toJson()),
                      ],
                    ),
                  ),
            Container(
              padding: const EdgeInsets.only(bottom: 10, top: 30),
              child: const Text(
                "Devices",
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey),
              ),
            ),
            viewModel.profile == null
                ? const Center(child: CircularProgressIndicator())
                : Container(
                    color: Colors.white,
                    child: Column(
                      children: [
                        GestureDetector(
                          onTap: () {
                            print("Tapped");
                            NavigationService().navigateToDeviceView(
                                showExistingDevices: true);
                          },
                          child: NavOption("Devices", Icons.person_outline,
                              data: viewModel.getDevices(viewModel.profile!)),
                        ),
                      ],
                    ),
                  ),
            Container(
              padding: const EdgeInsets.only(bottom: 10, top: 30),
              child: const Text(
                "ABOUT",
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey),
              ),
            ),
            GestureDetector(
              onTap: () async {},
              child: Container(
                color: Colors.white,
                child: Column(
                  children: [
                    const NavOption(
                      "Contact Us",
                      Icons.contact_page_outlined,
                      data: {
                        "Email": "App_support@SP4ameya.com",
                        "Phone Number": "+91 99163 87717"
                      },
                    ),
                    clickable_nav_option.NavOption(
                        "FAQs", Icons.question_answer_outlined, () {
                      NavigationService().navigateToFaqView();
                    }),
                  ],
                ),
              ),
            ),
            verticalSpaceMedium,
            Container(
              color: Colors.white,
              child: Column(
                children: [
                  clickable_nav_option.NavOption("Logout", Icons.logout, () {
                    viewModel.signOut();
                  }),
                ],
              ),
            ),
            verticalSpaceMedium,
            Container(
              color: Colors.white,
              child: Column(
                children: [
                  clickable_nav_option.NavOption(
                      "Delete Account", Icons.delete_outlined, () {
                    viewModel.deleteAccount();
                  }),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  AccountViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      AccountViewModel();

  @override
  void onViewModelReady(AccountViewModel viewModel) {
    viewModel.init();
  }
}
