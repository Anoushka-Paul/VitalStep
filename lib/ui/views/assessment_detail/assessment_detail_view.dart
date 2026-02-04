import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/Model/Comment.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'assessment_detail_viewmodel.dart';

class AssessmentDetailView extends StackedView<AssessmentDetailViewModel> {
  const AssessmentDetailView(
      {Key? key,
      required this.assessment,
      this.patientUserId,
      this.isSpecialist})
      : super(key: key);
  final Assessment assessment;
  final int? patientUserId;
  final bool? isSpecialist;

  @override
  Widget builder(
    BuildContext context,
    AssessmentDetailViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      resizeToAvoidBottomInset: false,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text("Assessment Detail"),
        actions: [
          // IconButton(onPressed: () {}, icon: const Icon(Icons.picture_as_pdf))
        ],
      ),
      body: Container(
        padding: const EdgeInsets.only(left: 25.0, right: 25.0),
        child: Column(
          children: [
            verticalSpaceMedium,
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text(
                  "BMI -",
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                horizontalSpaceMedium,
                viewModel.busy(viewModel.calculatingBMI)
                    ? const CircularProgressIndicator()
                    : Text(
                        viewModel.bmi.toString(),
                        style: const TextStyle(
                          fontSize: 20,
                        ),
                      ),
              ],
            ),
            verticalSpaceMedium,
            viewModel.busy(viewModel.calculatingDates)
                ? const Center(child: CircularProgressIndicator())
                : SizedBox(
                    width: double.infinity,
                    child: DataTable(
                      border: TableBorder.all(),
                      columns: const [
                        DataColumn(label: Text('First Date')),
                        DataColumn(label: Text('Last Date')),
                      ],
                      rows: [
                        DataRow(cells: [
                          DataCell(Text(viewModel.startDate)),
                          DataCell(Text(viewModel.endDate)),
                        ]),
                      ],
                    ),
                  ),
            verticalSpaceMedium,
            InkWell(
              onTap: () {
                NavigationService().navigateToAssessmentHistoryView(
                    assessment: assessment, patientId: patientUserId);
              },
              child: Container(
                  color: const Color(0xff2196f3),
                  width: screenWidth(context),
                  height: 50,
                  child: const Center(
                      child: Text(
                    "See Assessment History",
                    style: TextStyle(color: Colors.white, fontSize: 16),
                  ))),
            ),
            verticalSpaceMedium,
            isSpecialist == true
                ? const SizedBox()
                : InkWell(
                    onTap: () {
                      final dialogService = locator<DialogService>();
                      dialogService.showCustomDialog(
                          variant: DialogType.setReminder,
                          data: assessment.toJson());
                    },
                    child: Container(
                        color: const Color(0xff2196f3),
                        width: screenWidth(context),
                        height: 50,
                        child: Center(
                            child: Text(
                          "Set ${assessment.type} Reminder",
                          style: const TextStyle(
                              color: Colors.white, fontSize: 16),
                        ))),
                  ),
            verticalSpaceMedium,
            const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  "Remarks",
                  style: TextStyle(fontSize: 16),
                ),
              ],
            ),
            Expanded(
              child: FutureBuilder<List<Comment>>(
                  future: viewModel.comments,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    } else if (snapshot.connectionState ==
                        ConnectionState.done) {
                      if (snapshot.hasError) {
                        return const Center(child: Text("Error"));
                      } else if (snapshot.hasData) {
                        final comments = snapshot.data;
                        if (comments == null) {
                          return const Center(child: Text("Error"));
                        } else if (comments.isEmpty) {
                          return const Center(child: Text("No Comments"));
                        } else if (comments.isNotEmpty) {
                          return SizedBox(
                            height: 400,
                            child: ListView.builder(
                                itemCount: comments.length,
                                itemBuilder: (BuildContext context, int index) {
                                  return ListTile(
                                    title: Text(comments[index].remarks),
                                    subtitle: Text(
                                        "${viewModel.getDateAndTime(comments[index].createdAt.toLocal())}"),
                                    trailing: isSpecialist == true
                                        ? IconButton(
                                            onPressed: () async {
                                              await viewModel.deleteRemark(
                                                  id: comments[index].id);
                                              viewModel.comments = null;
                                              viewModel.rebuildUi();
                                              viewModel.comments =
                                                  viewModel.getComments(
                                                      assessmentId:
                                                          assessment.id);
                                            },
                                            icon: const Icon(Icons.delete))
                                        : const SizedBox(),
                                  );
                                }),
                          );
                        }
                      }
                    }
                    return const SizedBox();
                  }),
            ),
            // Spacer(),
            isSpecialist == true
                ? SizedBox(
                    width: double.infinity,
                    child: MaterialButton(
                      onPressed: () async {
                        final dialogService = locator<DialogService>();
                        await dialogService.showCustomDialog(
                            variant: DialogType.addComment,
                            data: assessment.toJson());
                        viewModel.comments = null;
                        viewModel.rebuildUi();
                        viewModel.comments =
                            viewModel.getComments(assessmentId: assessment.id);
                      },
                      color: Colors.blue,
                      textColor: Colors.white,
                      child: const Text("Add Comment"),
                    ),
                  )
                : const SizedBox()
          ],
        ),
      ),
    );
  }

  @override
  AssessmentDetailViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      AssessmentDetailViewModel();

  @override
  void onViewModelReady(AssessmentDetailViewModel viewModel) {
    viewModel.patientUserId = patientUserId;
    viewModel.getBMI();
    viewModel.getDates(assessmentId: assessment.id);
    viewModel.comments = viewModel.getComments(assessmentId: assessment.id);
  }
}
