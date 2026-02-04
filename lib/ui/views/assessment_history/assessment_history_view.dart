import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'assessment_history_viewmodel.dart';

class AssessmentHistoryView extends StackedView<AssessmentHistoryViewModel> {
  const AssessmentHistoryView(
      {Key? key, required this.assessment, this.patientId})
      : super(key: key);
  final Assessment assessment;
  final int? patientId;

  @override
  Widget builder(
    BuildContext context,
    AssessmentHistoryViewModel viewModel,
    Widget? child,
  ) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: Colors.white,
        appBar: AppBar(
          backgroundColor: Colors.white,
          title: const Text("Assessment History"),
          centerTitle: true,
          actions: [
            // IconButton(
            //     onPressed: () {
            //       viewModel.generatePDF(assessmentId: assessment.id);
            //     },
            //     icon: const Icon(Icons.picture_as_pdf))
          ],
          bottom: const TabBar(
            tabs: [
              Tab(
                text: "Table",
              ),
              Tab(
                text: "Graph",
              ),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            TableView(viewModel: viewModel, assessment: assessment),
            GraphView(
              viewModel: viewModel,
            )
          ],
        ),
      ),
    );
  }

  @override
  AssessmentHistoryViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      AssessmentHistoryViewModel();

  @override
  void onViewModelReady(AssessmentHistoryViewModel viewModel) async {
    viewModel.init(assessmentId: assessment.id, patientUserId: patientId);
    await viewModel.getDominantHand(patientId: patientId);
  }
}

class Loading extends StatelessWidget {
  const Loading({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
        height: 200, child: Center(child: CircularProgressIndicator()));
  }
}

class TableView extends StatelessWidget {
  const TableView({
    super.key,
    required this.viewModel,
    required this.assessment,
  });
  final AssessmentHistoryViewModel viewModel;
  final Assessment assessment;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.only(left: 25.0, right: 25.0),
      child: ListView(
        // crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          verticalSpaceMedium,
          // We will show a table
          const Text(
            "Right Hand Table",
            style: TextStyle(fontSize: 20),
          ),
          // right hand table
          SizedBox(
            height: 200,
            child: SingleChildScrollView(
              scrollDirection: Axis.vertical,
              child: viewModel.tests == null
                  ? const Loading()
                  : viewModel.tests!.isEmpty
                      ? Center(
                          child: Text("No Test Available"),
                        )
                      : SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            columns: const [
                              DataColumn(label: Text('ID')),
                              DataColumn(label: Text('Date')),
                              DataColumn(label: Text('Trial 1(Kg)')),
                              DataColumn(label: Text('Trial 2(Kg)')),
                              DataColumn(label: Text('Trial 3(Kg)')),
                              DataColumn(label: Text('Average')),
                              DataColumn(label: Text('Delete Test')),
                            ],
                            rows: viewModel
                                .getHandTests(hand: "Right", isAscending: false)
                                .map((test) {
                              return DataRow(cells: [
                                DataCell(Text(test.id.toString())),
                                DataCell(
                                    Text(viewModel.getDate(test.createdAt))),
                                DataCell(Text(test.trial1)),
                                DataCell(Text(test.trial2)),
                                DataCell(Text(test.trial3)),
                                DataCell(
                                    Text(viewModel.calculateAverage(test))),
                                DataCell(IconButton(
                                  icon: const Icon(Icons.delete),
                                  onPressed: () {
                                    viewModel.deleteTest(
                                        id: test.id,
                                        assessmentId: assessment.id);
                                  },
                                )),
                              ]);
                            }).toList(),
                          ),
                        ),
            ),
          ),
          verticalSpaceMedium,

          const Text(
            "Left Hand Table",
            style: TextStyle(fontSize: 20),
          ),
          // right hand table
          SizedBox(
            height: 200,
            child: SingleChildScrollView(
              scrollDirection: Axis.vertical,
              child: viewModel.tests == null
                  ? const Loading()
                  : viewModel.tests!.isEmpty
                      ? Center(
                          child: Text("No Test Available"),
                        )
                      : SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            columns: const [
                              DataColumn(label: Text('ID')),
                              DataColumn(label: Text('Date')),
                              DataColumn(label: Text('Trial 1(Kg)')),
                              DataColumn(label: Text('Trial 2(Kg)')),
                              DataColumn(label: Text('Trial 3(Kg)')),
                              DataColumn(label: Text('Average')),
                              DataColumn(label: Text('Delete Test')),
                            ],
                            rows: viewModel
                                .getHandTests(hand: "Left", isAscending: false)
                                .map((test) {
                              return DataRow(cells: [
                                DataCell(Text(test.id.toString())),
                                DataCell(
                                    Text(viewModel.getDate(test.createdAt))),
                                DataCell(Text(test.trial1)),
                                DataCell(Text(test.trial2)),
                                DataCell(Text(test.trial3)),
                                DataCell(
                                    Text(viewModel.calculateAverage(test))),
                                DataCell(IconButton(
                                  icon: const Icon(Icons.delete),
                                  onPressed: () {
                                    viewModel.deleteTest(
                                        id: test.id,
                                        assessmentId: assessment.id);
                                  },
                                )),
                              ]);
                            }).toList(),
                          ),
                        ),
            ),
          ),
          // latest test table.
          verticalSpaceMedium,
          const Text(
            "Latest Test",
            style: TextStyle(fontSize: 20),
          ),
          viewModel.tests == null
              ? const Loading()
              : viewModel.tests!.isEmpty
                  ? Center(
                      child: Text("No Test Available"),
                    )
                  : DataTable(columns: const [
                      DataColumn(label: Text('RH')),
                      DataColumn(label: Text('LH')),
                      DataColumn(label: Text('Difference')),
                    ], rows: [
                      DataRow(cells: [
                        DataCell(Text(
                            viewModel.getLatestTestAverage(hand: "Right"))),
                        DataCell(
                            Text(viewModel.getLatestTestAverage(hand: "Left"))),
                        DataCell(Text(viewModel.getLatestAverageDifference())),
                      ])
                    ]),

          // we will show a graph
          // two graphs - one bar showing the latest test result
          // one showing the progress of left and right hand
        ],
      ),
    );
  }
}

class GraphView extends StatelessWidget {
  const GraphView({super.key, required this.viewModel});
  final AssessmentHistoryViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: ListView(
        children: [
          verticalSpaceMedium,
          const Text(
            "Right Hand Graph",
            style: TextStyle(fontSize: 20),
          ),
          verticalSpaceMedium,
          // right hand graph
          SizedBox(
            height: 200,
            width: 200,
            child: viewModel
                    .getHandTests(hand: "Right", isAscending: true)
                    .isEmpty
                ? const Center(
                    child: Text("No data"),
                  )
                : LineChart(
                    LineChartData(
                      titlesData: FlTitlesData(
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              final date = DateTime.fromMillisecondsSinceEpoch(
                                  value.toInt());
                              if (value == meta.min) {
                                return Text(
                                  "${date.day}/${date.month}",
                                  style: const TextStyle(fontSize: 10),
                                );
                              } else if (value == (meta.max / 2)) {
                                return Text(
                                  "${date.day}/${date.month}",
                                  style: const TextStyle(fontSize: 10),
                                );
                              } else if (value == meta.max) {
                                return Text(
                                  "${date.day}/${date.month}",
                                  style: const TextStyle(fontSize: 10),
                                );
                              }
                              return const Text("");
                            },
                          ),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              if (value == 0) {
                                return const Text("0");
                              } else if (value == meta.max) {
                                return Text(value.toString());
                              }
                              return Text("");
                            },
                          ),
                        ),
                        rightTitles: const AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: false,
                          ),
                        ),
                        topTitles: const AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: false,
                          ),
                        ),
                      ),
                      minX: viewModel.tests!.isNotEmpty
                          ? viewModel
                              .tests!.first.createdAt.millisecondsSinceEpoch
                              .toDouble()
                          : 0,
                      maxX: viewModel.tests!.isNotEmpty
                          ? viewModel
                              .tests!.last.createdAt.millisecondsSinceEpoch
                              .toDouble()
                          : 10,
                      minY: 0,
                      maxY: viewModel.tests!.map((test) {
                        final y = viewModel.calculateAverage(test);
                        return double.parse(y);
                      }).reduce(max),
                      borderData:
                          FlBorderData(show: true, border: Border.all()),
                      lineBarsData: [
                        LineChartBarData(
                            color: viewModel.dominantHand == "Left"
                                ? Colors.green
                                : Colors.red,
                            spots: [
                              // FlSpot(0, 0),
                              ...viewModel
                                  .getHandTests(hand: "Left", isAscending: true)
                                  .map((test) {
                                final x = test.createdAt.millisecondsSinceEpoch
                                    .toDouble();
                                final y = viewModel.calculateAverage(test);
                                return FlSpot(x, double.parse(y));
                              }).toList(),
                            ]),
                        LineChartBarData(
                            color: viewModel.dominantHand == "Right"
                                ? Colors.green
                                : Colors.red, // isCurved: true,
                            spots: [
                              // FlSpot(0, 0),
                              ...viewModel
                                  .getHandTests(
                                      hand: "Right", isAscending: true)
                                  .map((test) {
                                final x = test.createdAt.millisecondsSinceEpoch
                                    .toDouble();
                                final y = viewModel.calculateAverage(test);
                                return FlSpot(x, double.parse(y));
                              }).toList(),
                            ]),
                      ],
                    ),
                  ),
          ),

          // latest test graph
          verticalSpaceMedium,
          const Text(
            "Latest Test Graph",
            style: TextStyle(fontSize: 20),
          ),
          verticalSpaceMedium,
          SizedBox(
            height: 200,
            width: 200,
            child:
                viewModel.getHandTests(hand: "Right", isAscending: true).isEmpty
                    ? const Center(
                        child: Text("No data"),
                      )
                    : BarChart(BarChartData(
                        titlesData: FlTitlesData(
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              getTitlesWidget: (value, meta) {
                                String title = "";
                                if (value == 0) {
                                  title = "0";
                                } else if (value == meta.appliedInterval ~/ 2) {
                                  title = value.toInt().toString();
                                } else if (value == meta.max) {
                                  title = value.toInt().toString();
                                }
                                return SideTitleWidget(
                                    axisSide: meta.axisSide,
                                    child: Text(title));
                              },
                            ),
                          ),
                          rightTitles: const AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: false,
                            ),
                          ),
                          topTitles: const AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: false,
                            ),
                          ),
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              getTitlesWidget: (value, meta) {
                                return Text(
                                  value == 0 ? "Right" : "Left",
                                  style: const TextStyle(fontSize: 16),
                                );
                              },
                            ),
                          ),
                        ),
                        minY: 0,
                        maxY: viewModel.getMaxAverageOfLastTest() + 5,
                        borderData: FlBorderData(
                            show: true,
                            border: const Border(
                                bottom: BorderSide(color: Colors.black),
                                left: BorderSide(color: Colors.black))),
                        barGroups: [
                          BarChartGroupData(
                            x: 0,
                            barRods: [
                              BarChartRodData(
                                toY: double.tryParse(viewModel
                                        .getLatestTestAverage(hand: "Right")) ??
                                    0,
                                color: viewModel.dominantHand == "Right"
                                    ? Colors.green
                                    : Colors.red,
                                width: 20,
                              ),
                            ],
                          ),
                          BarChartGroupData(
                            x: 1,
                            barRods: [
                              BarChartRodData(
                                toY: double.tryParse(viewModel
                                        .getLatestTestAverage(hand: "Left")) ??
                                    0,
                                color: viewModel.dominantHand == "Left"
                                    ? Colors.green
                                    : Colors.red,
                                width: 20,
                              ),
                            ],
                          ),
                        ],
                      )),
          ),
        ],
      ),
    );
  }
}
