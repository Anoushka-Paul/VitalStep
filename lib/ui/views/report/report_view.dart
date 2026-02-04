import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/ScreenHeading.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/widgets/common/graph_segment/graph_segment.dart';
import 'package:vital_step/ui/widgets/common/tabular_segment/tabular_segment.dart';

import 'report_viewmodel.dart';

class ReportView extends StackedView<ReportViewModel> {
  const ReportView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    ReportViewModel viewModel,
    Widget? child,
  ) {
    String selectedOption = "Graph";
    String selectedDateRange = "7 Days";
    List<String> options = ["Graph", "Data", "Send"];
    String? selectedPeriod;
    final List<String> periods = ['7 days', '1 month', '6 months', 'custom'];

    // Sample data for the table
    final List<Map<String, dynamic>> sampleData = [
      {'week': 1, 'left': 40, 'right': 37, 'fbw_diff': 3},
      {'week': 2, 'left': 45, 'right': 34, 'fbw_diff': 11},
      {'week': 3, 'left': 43, 'right': 42, 'fbw_diff': 1},
      {'week': 4, 'left': 46, 'right': 41, 'fbw_diff': 5},
      {'week': 5, 'left': 46, 'right': 37, 'fbw_diff': 9},
      {'week': 6, 'left': 46, 'right': 46, 'fbw_diff': 0},
      {'week': 7, 'left': 46, 'right': 46, 'fbw_diff': 0},
    ];

    List<String> durationType = ["7 days", "1month", "custom"];

    DateTime? fromDate;
    DateTime? toDate;
    Future<void> _selectDate(BuildContext context, bool isFromDate) async {
      DateTime initialDate = isFromDate
          ? (fromDate ?? DateTime.now())
          : (toDate ?? DateTime.now());
      DateTime firstDate = DateTime(2000);
      DateTime lastDate = DateTime(2101);

      final DateTime? picked = await showDatePicker(
        context: context,
        initialDate: initialDate,
        firstDate: firstDate,
        lastDate: lastDate,
      );
      if (picked != null && picked != initialDate) {
        if (isFromDate) {
          fromDate = picked;
        } else {
          toDate = picked;
        }
        viewModel.notifyListeners();
      }
    }

    return Column(
      children: [
        ScreenHeading(
          heading: "Report",
          showBackButton: false,
        ),
        DropdownButton<String>(
          value: selectedPeriod,
          hint: Text('Select a period'),
          onChanged: (String? newValue) {
            selectedPeriod = newValue;
            viewModel.notifyListeners();

            if (newValue == 'custom') {
              // Handle the 'custom' option here
              // For example, you could show a dialog to select a custom date range
              showCustomDateRangeDialog(context);
            }
          },
          items: periods.map<DropdownMenuItem<String>>((String value) {
            return DropdownMenuItem<String>(
              value: value,
              child: Text(value),
            );
          }).toList(),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            ElevatedButton(
              onPressed: () => _selectDate(context, true),
              child: Text(fromDate == null
                  ? 'Select From Date'
                  : 'From: ${fromDate.toString().split(' ')[0]}'),
            ),
            ElevatedButton(
              onPressed: () => _selectDate(context, false),
              child: Text(toDate == null
                  ? 'Select To Date'
                  : 'To: ${toDate.toString().split(' ')[0]}'),
            ),
          ],
        ),
        SizedBox(height: 10),
        Container(
          margin: EdgeInsets.symmetric(horizontal: 20),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(6),
              border: Border.all(width: 1, color: Colors.grey)),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: options.map((option) {
              return GestureDetector(
                onTap: () {
                  selectedOption = option;
                  viewModel.rebuildUi();
                },
                child: Container(
                  height: 30,
                  width: ((MediaQuery.of(context).size.width - 42) /
                      options.length),
                  decoration: BoxDecoration(
                    color: option == selectedOption
                        ? kcPrimaryColor
                        : Colors.white,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Center(
                    child: Text(
                      option,
                      style: TextStyle(
                        fontSize: 14,
                        color: option == selectedOption
                            ? Colors.white
                            : Colors.black,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
        SizedBox(
          height: 20,
        ),
        if (selectedOption == "Graphx") GraphSegment(data: sampleData),
        if (selectedOption == "Data") TabularSegment(data: sampleData),
      ],
    );
  }

  @override
  ReportViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      ReportViewModel();

  void showCustomDateRangeDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Select Custom Date Range'),
          content: Text('Implement custom date range selection here.'),
          actions: <Widget>[
            TextButton(
              child: Text('OK'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }
}
