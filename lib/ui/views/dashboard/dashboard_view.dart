import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'dashboard_viewmodel.dart';

class DashboardView extends StackedView<DashboardViewModel> {
  const DashboardView({Key? key}) : super(key: key);

  @override
  Widget builder(BuildContext context, DashboardViewModel viewModel, Widget? child) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          "Insights",
          style: TextStyle(
            color: kcDarkGreyColor,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.share_outlined, color: kcMediumGrey),
            onPressed: () {},
          ),
        ],
      ),
      body: viewModel.isBusy
          ? const Center(child: CircularProgressIndicator())
          : !viewModel.hasData
              ? _buildEmpty()
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Overview Metric
                      _buildMainStats(viewModel),
                      verticalSpaceMedium,

                      _buildSectionTitle("Grip Trends"),
                      verticalSpaceSmall,
                      _buildTrendGraph(viewModel),
                      verticalSpaceMedium,

                      _buildSectionTitle("Weekly Performance"),
                      verticalSpaceSmall,
                      _buildWeeklySummary(viewModel),
                      verticalSpaceMedium,

                      _buildSectionTitle("Assessment Breakdown"),
                      verticalSpaceSmall,
                      _buildPostureBreakdown(viewModel),
                      verticalSpaceLarge,
                    ],
                  ),
                ),
    );
  }

  Widget _buildMainStats(DashboardViewModel viewModel) {
    return Row(
      children: [
        _buildStatTile("Total Tests", "${viewModel.totalTests}", kcSecondaryColor),
        horizontalSpaceSmall,
        _buildStatTile("This Week", "${viewModel.thisWeekTests}", kcPrimaryColor),
      ],
    );
  }

  Widget _buildStatTile(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: premiumCardDecoration,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: kcMediumGrey, fontWeight: FontWeight.w600, fontSize: 13)),
            verticalSpaceTiny,
            Text(value, style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: color)),
          ],
        ),
      ),
    );
  }

  Widget _buildTrendGraph(DashboardViewModel viewModel) {
    return Container(
      height: 220,
      padding: const EdgeInsets.fromLTRB(10, 20, 20, 10),
      decoration: premiumCardDecoration,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 30, getTitlesWidget: (v, m) => Text(v.toInt().toString(), style: const TextStyle(fontSize: 10, color: kcMediumGrey)))),
            bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            if (viewModel.leftSpots.isNotEmpty)
              LineChartBarData(
                spots: viewModel.leftSpots,
                isCurved: true,
                color: kcSecondaryColor,
                barWidth: 3,
                dotData: FlDotData(show: false),
                belowBarData: BarAreaData(show: true, color: kcSecondaryColor.withOpacity(0.05)),
              ),
            if (viewModel.rightSpots.isNotEmpty)
              LineChartBarData(
                spots: viewModel.rightSpots,
                isCurved: true,
                color: kcPrimaryColor,
                barWidth: 3,
                dotData: FlDotData(show: false),
                belowBarData: BarAreaData(show: true, color: kcPrimaryColor.withOpacity(0.05)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildWeeklySummary(DashboardViewModel viewModel) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: premiumCardDecoration,
      child: Column(
        children: [
          _buildWeeklyRow("Left Hand", viewModel.leftCurrentWeek, viewModel.leftLastWeek, kcSecondaryColor),
          const Divider(height: 30),
          _buildWeeklyRow("Right Hand", viewModel.rightCurrentWeek, viewModel.rightLastWeek, kcPrimaryColor),
        ],
      ),
    );
  }

  Widget _buildWeeklyRow(String hand, double current, double last, Color color) {
    bool improved = current >= last;
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle),
          child: Icon(Icons.back_hand, color: color, size: 20),
        ),
        horizontalSpaceSmall,
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(hand, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
              Text("Last week: ${last.toStringAsFixed(1)} Kg", style: const TextStyle(color: kcMediumGrey, fontSize: 12)),
            ],
          ),
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text("${current.toStringAsFixed(1)} Kg", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            Row(
              children: [
                Icon(improved ? Icons.arrow_upward : Icons.arrow_downward, color: improved ? kcSuccessColor : kcErrorColor, size: 12),
                Text(
                  "${((current - last).abs()).toStringAsFixed(1)} Kg",
                  style: TextStyle(color: improved ? kcSuccessColor : kcErrorColor, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: kcDarkGreyColor),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.insert_chart_outlined, size: 80, color: kcLightGrey),
          verticalSpaceMedium,
          const Text("No Trends Yet", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: kcDarkGreyColor)),
          verticalSpaceSmall,
          const Text("Keep testing to see your progress analysis.", textAlign: TextAlign.center, style: TextStyle(color: kcMediumGrey)),
        ],
      ),
    );
  }

  Widget _buildPostureBreakdown(DashboardViewModel vm) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.grey.withOpacity(0.08), blurRadius: 8)],
      ),
      child: Column(
        children: vm.postureAverages.entries.map((e) {
          final idx = vm.postureAverages.keys.toList().indexOf(e.key);
          final colors = [kcPrimaryColor, kcSecondaryColor, kcSuccessColor, Colors.orange, Colors.purple];
          final color = colors[idx % colors.length];
          return ListTile(
            leading: CircleAvatar(
              radius: 8,
              backgroundColor: color,
            ),
            title: Text(e.key,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            trailing: Text("${e.value.toStringAsFixed(1)} Kg",
                style: TextStyle(color: color, fontWeight: FontWeight.bold)),
          );
        }).toList(),
      ),
    );
  }

  @override
  DashboardViewModel viewModelBuilder(BuildContext context) => DashboardViewModel();

  @override
  void onViewModelReady(DashboardViewModel viewModel) => viewModel.init();
}
