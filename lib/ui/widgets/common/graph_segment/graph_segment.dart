import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/app_colors.dart';

import 'graph_segment_model.dart';

class GraphSegment extends StackedView<GraphSegmentModel> {
  const GraphSegment({super.key, required this.data});
  final List<Map<String, dynamic>> data;

  @override
  Widget builder(
    BuildContext context,
    GraphSegmentModel viewModel,
    Widget? child,
  ) {
    return Expanded(
      child: Container(
        width: double.infinity,
        color: kcPrimaryColor.withAlpha(30),
        child: SingleChildScrollView(
          child: Column(
            children: [
              SizedBox(
                height: 20,
              ),
              Container(
                margin: EdgeInsets.only(left: 20, right: 20, bottom: 15),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(5)),
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(8.0),
                      child: Text(
                        "Pressure Value Over Time",
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ),
                    Container(
                      height: 400,
                      width: double.infinity,
                      child: LineChart(
                        LineChartData(
                          gridData: FlGridData(show: true),
                          titlesData: FlTitlesData(show: true),
                          borderData: FlBorderData(
                            show: true,
                            border: Border.all(color: Colors.black, width: 1),
                          ),
                          lineBarsData: [
                            LineChartBarData(
                              spots: data
                                  .map((data) => FlSpot(
                                      data['timestamp']
                                          .millisecondsSinceEpoch
                                          .toDouble(),
                                      data['pressure_value'].toDouble()))
                                  .toList(),
                              isCurved: true,
                              barWidth: 4,
                              belowBarData: BarAreaData(show: false),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  GraphSegmentModel viewModelBuilder(
    BuildContext context,
  ) =>
      GraphSegmentModel();
}
