import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vital_step/Model/accounts.dart';
import 'package:vital_step/app/app.router.dart';

import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/widgets/common/glass_card.dart';
import 'package:fl_chart/fl_chart.dart';
import 'home_tab_viewmodel.dart';

class HomeTabView extends StackedView<HomeTabViewModel> {
  const HomeTabView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    HomeTabViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: kcVeryLightGrey,
      body: CustomScrollView(
        slivers: [
          _buildSliverAppBar(viewModel),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHealthInsightPrompt(viewModel),
                  verticalSpaceMedium,
                  _buildSectionHeader("Health Metrics"),
                  verticalSpaceSmall,
                  _buildQuickStats(viewModel),
                  verticalSpaceMedium,
                  _buildSectionHeader("Tools & Insights"),
                  verticalSpaceSmall,
                  _buildToolsGrid(viewModel),
                  verticalSpaceMedium,
                  _buildSectionHeader("Recent Specialists"),
                  verticalSpaceSmall,
                  _buildSpecialistsList(viewModel),
                  verticalSpaceLarge,
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthInsightPrompt(HomeTabViewModel vm) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [vm.healthStatusColor.withOpacity(0.05), Colors.white],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: vm.healthStatusColor.withOpacity(0.12), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: vm.healthStatusColor.withOpacity(0.04),
            blurRadius: 30,
            offset: const Offset(0, 15),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: vm.healthStatusColor.withOpacity(0.12), shape: BoxShape.circle),
                child: Icon(Icons.auto_awesome, color: vm.healthStatusColor, size: 20),
              ),
              horizontalSpaceSmall,
              const Text("Health Insight", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: kcDarkGreyColor)),
            ],
          ),
          verticalSpaceSmall,
          Text(
            vm.healthInsight,
            style: const TextStyle(fontSize: 14, height: 1.5, color: kcMediumGrey, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildSliverAppBar(HomeTabViewModel vm) {
    return SliverAppBar(
      expandedHeight: 120,
      floating: false,
      pinned: true,
      elevation: 0,
      backgroundColor: kcPrimaryColor,
      flexibleSpace: FlexibleSpaceBar(
        titlePadding: const EdgeInsets.only(left: 20, bottom: 16),
        title: Text(
          "Hello, ${vm.profile?.name?.split(' ')[0] ?? 'User'}",
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 20, letterSpacing: -0.5),
        ),
        background: Container(
          decoration: const BoxDecoration(
            gradient: kcPrimaryGradient,
          ),
          child: Stack(
            children: [
              Positioned(
                right: -20,
                top: -20,
                child: CircleAvatar(radius: 80, backgroundColor: Colors.white.withOpacity(0.05)),
              ),
            ],
          ),
        ),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 20, top: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                const Icon(Icons.local_fire_department, color: Colors.orange, size: 20),
                const SizedBox(width: 4),
                Text("${vm.streak}d", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: kcDarkGreyColor),
    );
  }


  Widget _buildQuickStats(HomeTabViewModel vm) {
    return Row(
      children: [
        _buildHealthMetricCard(
          title: "Left Hand",
          value: vm.leftHandStrength,
          trend: vm.leftHandValue,
          color: kcSecondaryColor,
          onTap: () => vm.startHandTest("Left"),
        ),
        horizontalSpaceSmall,
        _buildHealthMetricCard(
          title: "Right Hand",
          value: vm.rightHandStrength,
          trend: vm.rightHandValue,
          color: kcAccentColor,
          onTap: () => vm.startHandTest("Right"),
        ),
      ],
    );
  }

  Widget _buildHealthMetricCard({
    required String title,
    required String value,
    required String trend,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(0.06),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
            border: Border.all(color: color.withOpacity(0.05), width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title, style: const TextStyle(color: kcMediumGrey, fontWeight: FontWeight.w600, fontSize: 13)),
                  Icon(Icons.arrow_forward_ios, size: 10, color: color.withOpacity(0.5)),
                ],
              ),
              verticalSpaceSmall,
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(value, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: kcDarkGreyColor, letterSpacing: -1)),
                  const Padding(
                    padding: EdgeInsets.only(bottom: 4, left: 4),
                    child: Text("kg", style: TextStyle(color: kcMediumGrey, fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              verticalSpaceSmall,
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: color.withOpacity(0.08), borderRadius: BorderRadius.circular(12)),
                child: Text(trend, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildToolsGrid(HomeTabViewModel vm) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 3,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      children: [
        _buildToolIconCard("Analysis", Icons.analytics_outlined, Colors.purple, () => vm.navigateToAnalysis()),
        _buildToolIconCard("History", Icons.history_rounded, Colors.orange, () => NavigationService().navigateTo(Routes.assesmentView)),
        _buildToolIconCard("Compare", Icons.compare_arrows_rounded, Colors.blue, () => vm.navigateToCompare()),
      ],
    );
  }

  Widget _buildToolIconCard(String title, IconData icon, Color col, VoidCallback tap) {
    return InkWell(
      onTap: tap,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: kcLightGrey.withOpacity(0.3), width: 1),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: col.withOpacity(0.08), shape: BoxShape.circle),
              child: Icon(icon, color: col, size: 24),
            ),
            verticalSpaceSmall,
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: kcDarkGreyColor)),
          ],
        ),
      ),
    );
  }

  Widget _buildSpecialistsList(HomeTabViewModel viewModel) {
    return FutureBuilder<List<Accounts>>(
      future: viewModel.getSpecialists(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        } else if (snapshot.hasData && snapshot.data != null && snapshot.data!.isNotEmpty) {
          final accounts = snapshot.data!;
          return ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: accounts.length,
            separatorBuilder: (c, i) => verticalSpaceSmall,
            itemBuilder: (context, index) {
              final specialist = accounts[index].specialist;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: kcLightGrey.withOpacity(0.3), width: 1),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 25,
                        backgroundColor: kcPrimaryColor.withOpacity(0.1),
                        child: Text(specialist?.name[0] ?? "D", style: const TextStyle(color: kcPrimaryColor, fontWeight: FontWeight.bold, fontSize: 18)),
                      ),
                      horizontalSpaceSmall,
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(specialist?.name ?? "Unknown", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: kcDarkGreyColor)),
                            Text(specialist?.email ?? "No Email", style: const TextStyle(fontSize: 12, color: kcMediumGrey)),
                            if (specialist?.phone != null)
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text("${specialist?.countryCode ?? ''} ${specialist?.phone}", style: const TextStyle(fontSize: 12, color: kcPrimaryColor, fontWeight: FontWeight.w600)),
                              ),
                          ],
                        ),
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.call_rounded, color: kcSuccessColor, size: 22),
                            onPressed: () => viewModel.contactSpecialistViaCall(specialist?.phone),
                            constraints: const BoxConstraints(),
                          ),
                          IconButton(
                            icon: const Icon(Icons.message_rounded, color: Colors.green, size: 22),
                            onPressed: () => viewModel.contactSpecialistViaWhatsApp(specialist?.phone, specialist?.countryCode),
                            constraints: const BoxConstraints(),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        }
        return const Center(child: Text("No Specialists Found", style: TextStyle(color: kcMediumGrey)));
      },
    );
  }

  Widget _buildVideoCard({required String link, required String thumbNail}) {
    return InkWell(
      onTap: () => launchUrl(Uri.parse(link)),
      child: Container(
        height: 180,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          image: DecorationImage(
            image: AssetImage("assets/$thumbNail.png"),
            fit: BoxFit.cover,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black12,
              blurRadius: 10,
              offset: const Offset(0, 4),
            )
          ],
        ),
        child: Center(
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.8),
              shape: BoxShape.circle,
            ),
            child:
                const Icon(Icons.play_arrow, color: kcPrimaryColor, size: 40),
          ),
        ),
      ),
    );
  }

  @override
  HomeTabViewModel viewModelBuilder(BuildContext context) => HomeTabViewModel();

  @override
  onViewModelReady(HomeTabViewModel viewModel) {
    viewModel.init();
  }
}
