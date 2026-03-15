import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Device.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/views/account/account_viewmodel.dart';

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
      appBar: AppBar(
        title: const Text(
          "Profile",
          style: TextStyle(color: kcDarkGreyColor, fontWeight: FontWeight.bold),
        ),
        centerTitle: false,
        backgroundColor: Colors.white,
        elevation: 0,
      ),
      body: viewModel.isBusy
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _buildProfileHeader(viewModel),
                  verticalSpaceMedium,
                  
                  _buildSettingsGroup([
                    _buildSettingsItem(
                      icon: Icons.person_outline,
                      title: "Edit Profile",
                      onTap: () => NavigationService().navigateToSignUpView(profile: viewModel.profile),
                    ),
                    _buildSettingsItem(
                      icon: Icons.watch_outlined,
                      title: "My Devices",
                      onTap: () => NavigationService().navigateToDeviceView(showExistingDevices: true),
                    ),
                  ]),
                  verticalSpaceMedium,

                  _buildSettingsGroup([
                    _buildSettingsItem(
                      icon: Icons.contact_support_outlined,
                      title: "Contact Support",
                      onTap: () => viewModel.contactSupport(),
                    ),
                    _buildSettingsItem(
                      icon: Icons.question_answer_outlined,
                      title: "FAQs",
                      onTap: () => NavigationService().navigateToFaqView(),
                    ),
                  ]),
                  verticalSpaceLarge,

                  _buildActionButtons(viewModel),
                  verticalSpaceLarge,
                ],
              ),
            ),
    );
  }

  Widget _buildProfileHeader(AccountViewModel viewModel) {
    final profile = viewModel.profile;
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: premiumCardDecoration,
      child: Row(
        children: [
          Container(
            width: 70,
            height: 70,
            decoration: BoxDecoration(
              color: kcSecondaryColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.person, size: 40, color: kcSecondaryColor),
          ),
          horizontalSpaceMedium,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  profile?.name ?? "User",
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
                Text(
                  profile?.email ?? "No email provided",
                  style: const TextStyle(color: kcMediumGrey, fontSize: 14),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsGroup(List<Widget> items) {
    return Container(
      decoration: premiumCardDecoration,
      child: Column(
        children: items.asMap().entries.map((entry) {
          int idx = entry.key;
          Widget item = entry.value;
          return Column(
            children: [
              item,
              if (idx < items.length - 1)
                Divider(height: 1, color: Colors.grey.shade100, indent: 60),
            ],
          );
        }).toList(),
      ),
    );
  }

  Widget _buildSettingsItem({required IconData icon, required String title, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          children: [
            Icon(icon, color: kcMediumGrey, size: 22),
            horizontalSpaceMedium,
            Expanded(
              child: Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
              ),
            ),
            const Icon(Icons.chevron_right, color: kcLightGrey, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons(AccountViewModel viewModel) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 56,
          child: TextButton(
            onPressed: () => viewModel.signOut(),
            style: TextButton.styleFrom(
              backgroundColor: kcBackgroundColor,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: const Text(
              "Log Out",
              style: TextStyle(color: kcErrorColor, fontWeight: FontWeight.bold, fontSize: 16),
            ),
          ),
        ),
        verticalSpaceSmall,
        TextButton(
          onPressed: () => viewModel.deleteAccount(),
          child: const Text(
            "Delete Account",
            style: TextStyle(color: kcMediumGrey, fontSize: 13),
          ),
        ),
      ],
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
